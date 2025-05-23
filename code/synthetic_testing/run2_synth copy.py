import subprocess
import json
import os
import time
import glob
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import functions as fnc
        

# Define the paths to the scripts you want to run
first_second_run = "code/First_second_pass_newtile.py"
Merging_window = "code/Merging_window_newtile.py"
Third_pass = 'code/Third_pass_newtile.py'
Third_pass_b = 'code/Third_pass_newtile_b.py'
noti='/DATA/vito/code/notification.py'
ac_py = 'code/synthetic_testing/ran_synth_point_ac.py'
DS='ran_synth_16_bw'
if not os.path.exists('/DATA/vito/data/'+DS+'/'+DS):
            os.makedirs('/DATA/vito/data/'+DS+'/'+DS)
            print('Created '+'/DATA/vito/data/'+DS+'/'+DS)
subprocess.run(["python", ac_py, 'ran_synth_16_bw'])
subprocess.run(["python", noti, 'ran_synth_16_bw'])

DSL=[#'ran_synth_08_bw'
     #,'ran_synth_16_bw'
     #,'ran_synth_32_bw'
     #,'ran_synth_64_bw'
     #,'ran_synth_64_cl_std_00'
     #,'ran_synth_64_cl_std_03'
     #,'ran_synth_64_cl_std_06'
     #,'ran_synth_64_cl_std_12'
     #,'ran_synth_64_cl_std_24'
     #,'ran_synth_08_bw_rt'
     #'ran_synth_01_10_bw'
     'ran_synth_04_100_bw'
     ,'ran_synth_08_100_bw'
     #,'ran_synth_01_100_bw'
     #,'ran_synth_02_3000_bw'
     #,'ran_synth_04_3000_bw'
     #,'ran_synth_01_10_cl_std_00'
     #,'ran_synth_01_10_cl_std_03'
     #,'ran_synth_01_10_cl_std_06'
     #,'ran_synth_01_10_cl_std_12'
     #,'ran_synth_01_10_cl_std_24'
     ]


for DS in DSL:
    if not os.path.exists(f'/DATA/vito/output/{DS}'):
        os.makedirs(f'/DATA/vito/output/{DS}')
    para_list=[]
    for i in range(12):
        para_list.append({'OutDIR': f'/DATA/vito/output/{DS}/{DS}_{i:02}_b250/',
                            'DataDIR': '/DATA/vito/data/',
                            'DatasetName': f'{DS}/img/*',
                            'fid': i,
                            'crop_size': 1024,
                            'resample_factor': 1,
                            'point_per_side': 30,
                            'dilation_size':15,
                            'b':250,
                            'stability_t':0.85,
                            'third_b_resample_factor':1/12, #None: use method A. 1: auto select resample rate.
                            'resolution(mm)': 0.2,
                            'expected_min_size(sqmm)': 0,
                            'min_radius': 0
                            }
                            )

    for para in para_list:
        start_run = time.time()
        if para.get('fid')==None:
            if not os.path.exists(para.get('DataDIR')+para.get('DatasetName')[:-1]):
                print(f'Input directory {para.get('DataDIR')+para.get('DatasetName')}does not exist. Exiting script.')
                sys.exit()
            fn_img = glob.glob(para.get('DataDIR')+para.get('DatasetName'))
            fn_img.sort()
            for i,fn in enumerate(fn_img):
                print(i, ': ', fn)
            print('--------------')
            while True:
                try:
                    user_input = int(input("Please select an image: "))
                    print(f"{fn_img[user_input]} selected")
                    para.update({'fid':user_input})
                    break  # Exit the loop if the input is valid
                except ValueError:
                    print("Requires an index. Please try again.")
        resample_factor=para.get('resample_factor')
        pre_para={'Resample': {'fxy':resample_factor},
                }
        
        OutDIR=para.get('OutDIR')
        third_b=para.get('third_b_resample_factor')

        # create dir if output dir not exist
        fnc.create_dir_ifnotexist(OutDIR)

        # Save init_para to a JSON file
        with open(OutDIR+'init_para.json', 'w') as json_file:
            json.dump(para, json_file, indent=4)
        with open(OutDIR+'pre_para.json', 'w') as json_file:
            json.dump(pre_para, json_file, indent=4)

        print('Performing first pass and second pass clipwise segmentation')
        subprocess.run(["python", first_second_run, OutDIR])

        print('Merging windows')
        subprocess.run(["python", Merging_window, OutDIR])

        for n in range(len(third_b)):
            if not third_b[n]:
                print('Searching potential missing objects and performing third pass segmentation A')
                subprocess.run(["python", Third_pass, OutDIR,f'{n}'])
            else:
                print('Searching potential missing objects and performing third pass segmentation B')
                subprocess.run(["python", Third_pass_b, OutDIR,f'{n}'])

        end_run = time.time()
        print('Run took: ', end_run-start_run)

    print(f'{DS} completed')
    subprocess.run(["python", noti, DS])

    print('Working on '+DS)
    if not os.path.exists('/DATA/vito/data/'+DS+'/'+DS):
            os.makedirs('/DATA/vito/data/'+DS+'/'+DS)
            print('Created '+'/DATA/vito/data/'+DS+'/'+DS)
    print(DS)
    subprocess.run(["python", ac_py, DS])
    subprocess.run(["python", noti, DS])


subprocess.run(["python", noti, sys.argv[0]])
