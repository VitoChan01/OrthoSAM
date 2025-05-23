import torch
from segment_anything import sam_model_registry, SamPredictor
from automatic_mask_generator_mod import SamAutomaticMaskGenerator
import numpy as np
import torch
import gc
import os
import time
import sys
import json
import os
from utility import set_sam, load_image, preprocessing_roulette, get_patch_at, clean_mask, area_radi, nms
from Layer_0 import filter_by_pred_iou_and_size_per_seedpoint, Groupping_masks, filter_groupping_by_intersection, checking_remaining_ungroupped, Guided_second_pass_SAM, mask_in_valid_box
start_script = time.time()

OutDIR=sys.argv[1]
clip_i=int(sys.argv[2])
clip_j=int(sys.argv[3])
max_ij=int(sys.argv[4])

ij_idx = (clip_i,clip_j)


n_pass=len(os.listdir(os.path.join(OutDIR,'Merged')))
if not os.path.exists(os.path.join(OutDIR,f'chunks/{n_pass}')):
    os.makedirs(os.path.join(OutDIR,f'chunks/{n_pass}'))
with open(os.path.join(OutDIR,'para.json'), 'r') as json_file:
    para = json.load(json_file)[n_pass]
print('Loaded parameters from json')
print(para)


DataDIR=para.get('DataDIR')
DSname=para.get('DatasetName')
fid=para.get('fid')
pps=para.get('input_point_per_axis')
b=para.get('tile_overlap')
stb_t=para.get('stability_t')
#defining clips
crop_size=para.get('tile_size')
resample_factor=para.get('resample_factor')
min_pixel=(para.get('expected_min_size(sqmm)')/(para.get('resolution(mm)')**2))*resample_factor
min_radi=para.get('min_radius')
print(f'Minimum expected size: {min_pixel} pixel')


try:#attempt to load saved pre_para
    with open(OutDIR+'pre_para.json', 'r') as json_file:
        pre_para = json.load(json_file)[n_pass]
    pre_para.update({'Resample': {'fxy':resample_factor}})
    print('Loaded preprocessing parameters from json')
    print(pre_para)
except:#use defined init_para
    print('Using preprocessing default')
    pre_para={'Resample': {'fxy':resample_factor}}
    print(pre_para)

#Prep
#load image
image=load_image(DataDIR,DSname,fid)
print('Image size:', image.shape)
image=preprocessing_roulette(image, pre_para)

patche = get_patch_at(image, clip_i,clip_j, crop_size, 2*b)

#setup SAM
sam=set_sam(para.get('MODEL_TYPE'), para.get('CheckpointDIR'))
mask_generator = SamAutomaticMaskGenerator(sam)


start_loop = time.time()
print(f'Segmenting clip: {ij_idx}')
#prepare image
temp_image=patche
if (temp_image.shape[0]>(crop_size//8) and temp_image.shape[1]>(crop_size//8)):
    if len(np.unique(temp_image))>1:
        #clear gpu ram
        gc.collect()
        torch.cuda.empty_cache()

        #SAM segmentation
        mask_generator = SamAutomaticMaskGenerator(
            model=sam,
            points_per_side=pps,
            pred_iou_thresh=0,
            stability_score_thresh=stb_t,#iou by varying cutoff in binary conversion
            box_nms_thresh=0.3,#The box IoU cutoff used by non-maximal suppression to filter duplicate masks
            crop_n_layers=0,#cut into 2**n crops
            crop_nms_thresh=0,#The box IoU cutoff used by non-maximal suppression to filter duplicate masks between crops
            crop_n_points_downscale_factor=1,
            crop_overlap_ratio=0,
            #min_mask_region_area=2000,
        )

        with torch.no_grad():
            masks = mask_generator.generate(temp_image)
        print('First pass SAM: ', len(masks),' mask(s) found')

        #post processing
        #filter output mask per point by select highest pred iou mask
        masks=filter_by_pred_iou_and_size_per_seedpoint(masks, crop_size)
        print('Filtered by highest predicted iou per seed point, ', len(masks),' mask(s) remains')

        list_of_pred_iou = [mask['predicted_iou'] for mask in masks]
        list_of_masks = [clean_mask(mask['segmentation'].astype('bool')) for mask in masks]#remove small disconnected parts
        no_area_after_cleaning=np.array([np.sum(mask)==0 for mask in list_of_masks])
        area_radi=np.array([area_radi(mask, min_pixel, min_radi) for mask in list_of_masks])
        if np.any(no_area_after_cleaning):
            list_of_masks = [mask for mask, keep in zip(list_of_masks, ~no_area_after_cleaning) if keep]
            list_of_pred_iou = [iou for iou, keep in zip(list_of_pred_iou, ~no_area_after_cleaning) if keep]
        if not np.all(area_radi):
            list_of_masks = [mask for mask, keep in zip(list_of_masks, area_radi) if keep]
            list_of_pred_iou = [iou for iou, keep in zip(list_of_pred_iou, area_radi) if keep]
        #remove background/edge mask
        flattened_rgb=np.sum(temp_image,axis=2)
        not_background_mask=np.array([np.any(flattened_rgb[mask.astype('bool')]>0) for mask in list_of_masks])
        if not np.all(not_background_mask):
            list_of_masks = [mask for mask, keep in zip(list_of_masks, not_background_mask) if keep]
            list_of_pred_iou = [mask for mask, keep in zip(list_of_pred_iou, not_background_mask) if keep]
            print('Background masks removed')
        
        if len(list_of_masks)>0:
            #grouping overlaps
            list_of_cleaned_groups_reseg_masks_nms, list_of_cleaned_groups_reseg_score_nms=[],[]
            group_overlap_area, unique_groups, list_overlap = Groupping_masks(list_of_masks)
            unique_groups_thresholded = filter_groupping_by_intersection(group_overlap_area,unique_groups, list_overlap)
            cleaned_groups, list_of_nooverlap_mask = checking_remaining_ungroupped(list_of_masks, unique_groups_thresholded, masks)
            if cleaned_groups:
                predictor = SamPredictor(sam)
                predictor.set_image(temp_image)
                list_of_cleaned_groups_reseg_masks, list_of_cleaned_groups_reseg_score = Guided_second_pass_SAM(cleaned_groups, min_pixel, min_radi, list_of_masks, predictor, crop_size)
                if len(list_of_nooverlap_mask)>0:
                    for m in list_of_nooverlap_mask:
                        list_of_cleaned_groups_reseg_masks.append(list_of_masks[m].astype('bool'))
                        list_of_cleaned_groups_reseg_score.append(list_of_pred_iou[m])
                list_of_cleaned_groups_reseg_masks_nms, list_of_cleaned_groups_reseg_score_nms = nms(list_of_cleaned_groups_reseg_masks, list_of_cleaned_groups_reseg_score)
                print('Found ',len(list_of_cleaned_groups_reseg_score_nms), ' mask(s)/object(s) in the clip')
            else:
                list_of_cleaned_groups_reseg_masks, list_of_cleaned_groups_reseg_score = list_of_masks, list_of_pred_iou
                list_of_cleaned_groups_reseg_masks_nms, list_of_cleaned_groups_reseg_score_nms = nms(list_of_cleaned_groups_reseg_masks, list_of_cleaned_groups_reseg_score)
                print(f'No groups were found, found {len(list_of_cleaned_groups_reseg_masks)} mask(s) from the first pass')
                print(f'{len(list_of_cleaned_groups_reseg_masks_nms)} left after nms filtering')

            #valid box
            if len(list_of_cleaned_groups_reseg_masks_nms)>0:
                keep = mask_in_valid_box(list_of_cleaned_groups_reseg_masks_nms,b, ij_idx, max_ij)
                list_of_cleaned_groups_reseg_masks_nms=[list_of_cleaned_groups_reseg_masks_nms[i] for i,k in enumerate(keep) if k]
                list_of_cleaned_groups_reseg_score_nms=[list_of_cleaned_groups_reseg_score_nms[i] for i,k in enumerate(keep) if k]
                if len(list_of_cleaned_groups_reseg_masks_nms)>0:
                    msk_dic={#'mask':list_of_cleaned_groups_reseg_masks,
                                'nms mask':list_of_cleaned_groups_reseg_masks_nms,
                                #'mask pred iou':list_of_cleaned_groups_reseg_score,
                                'nms mask pred iou': list_of_cleaned_groups_reseg_score_nms,
                                'ij':ij_idx,'crop size':crop_size}
                    np.save(OutDIR+f'chunks/{n_pass}/chunk_{int(ij_idx[0])}_{int(ij_idx[1])}',[msk_dic])
                    del msk_dic, list_of_cleaned_groups_reseg_masks_nms, list_of_cleaned_groups_reseg_score_nms
            else:
                print('No valid mask were found inside valid box')
        else:
            print('No valid mask remains after background, area, and radius filtering')
    else:
        print('This crop is bacground/edge')
else:
    print('This crop is too small')            
end_loop = time.time()
print('loop took: ', end_loop-start_loop)


end_script = time.time()
print('script took: ', end_script-start_script)
print('First and second pass SAM completed. Output saved to '+OutDIR)

