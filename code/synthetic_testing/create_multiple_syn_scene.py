import subprocess

#for radi in [2,4]:
#    print('Creating scene with min radi: ', radi)
#    subprocess.run(["python", 'code/synthetic_testing/create_syn_scene.py', f'{radi}'])
#subprocess.run(["python", 'code/synthetic_testing/create_syn_scene.py', '4','100'])
#subprocess.run(["python", 'code/synthetic_testing/create_syn_scene.py', '8','100'])
#subprocess.run(["python", 'code/synthetic_testing/create_syn_scene.py', '1','10','True'])
#print('Add noise')
#subprocess.run(["python", 'code/synthetic_testing/create_syn_scene.py', '1','3000'])
#subprocess.run(["python", 'code/synthetic_testing/add_noise_syn_scene.py', '1','10'])
#subprocess.run(["python", 'code/synthetic_testing/create_syn_scene.py', '2','1500','True'])
#subprocess.run(["python", 'code/synthetic_testing/add_noise_syn_scene.py', '2','1500'])
subprocess.run(["python", 'code/synthetic_testing/create_syn_shadow.py', '12','1500', '0.1'])
subprocess.run(["python", 'code/synthetic_testing/create_syn_shadow.py', '12','1500'])
subprocess.run(["python", 'code/synthetic_testing/create_syn_shadow.py', '12','1500', '0.3'])
subprocess.run(["python", 'code/synthetic_testing/create_syn_shadow.py', '12','1500', '0.4'])
subprocess.run(["python", 'code/synthetic_testing/create_syn_shadow.py', '12','1500', '0.5'])
