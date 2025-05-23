import json
import time
import logging
from Layer_0 import predict_tiles
from Merging import merge_chunks
from Layer_n import predict_tiles_n
from notification import notify
import os
import sys
from pathlib import Path
class StreamToLogger:
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
        self.buffer = ''

    def write(self, message):
        if message.rstrip() != '':
            self.logger.log(self.level, message.rstrip())

    def flush(self):
        pass

def setup_full_logging(log_file_path='output.log'):
    # Create log directory if needed
    Path(log_file_path).parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file_path, mode='w'),
            logging.StreamHandler(sys.stdout)  # still show in terminal
        ]
    )

    # Redirect print(), warnings, errors
    sys.stdout = StreamToLogger(logging.getLogger(), logging.INFO)
    sys.stderr = StreamToLogger(logging.getLogger(), logging.ERROR)

def orthosam(para_list):
    #setup_full_logging('logs/output.log')
    # Save para to a JSON file
    OutDIR=para_list[0].get('OutDIR')
    #with open(os.path.join(OutDIR,'para.json'), 'r') as json_file:
    #    para_list = json.load(json_file)

    noti=para_list[0].get('fid')

    for n in range(len(para_list)):
        start_run_whole = time.time()
        if n==0:
            start_run = time.time()
            predict_tiles(para_list, n)
            end_run = time.time()       
            if noti:
                notify(OutDIR+' first pass completed. It took '+f'{end_run-start_run}')

            start_run = time.time()
            merge_chunks(para_list,n)
            end_run = time.time()
            if noti:
                notify(OutDIR+' first pass merging completed. It took '+f'{end_run-start_run}')
        else:
            #third_b=para_list[n].get('n_pass_resample_factor')
            #if not third_b:
            #    print('Searching potential missing objects and performing third pass segmentation A')
            #    subprocess.run(["python", Third_pass, OutDIR])
            #else:
            print('Searching potential missing objects and performing third pass segmentation B')
            start_run = time.time()
            predict_tiles_n(para_list, n)
            end_run = time.time()
            if noti:
                notify(OutDIR+f' {n} pass merging completed. It took '+f'{end_run-start_run}')
                
        end_run_whole = time.time()
        print('Run took: ', end_run_whole -start_run_whole )
    if noti:
        notify(OutDIR+' all layers completed')