import os
import xlsxwriter
import random
import time

# multimachine benchmarks configure
#-----------------------------------------------------------------------------------

models = ['resnet50', 'resnet152', 'inception3', 'alexnet', 'vgg16']
gpu_number = 1

# you can modify variable_update to ['parameter_server', 'distributed_replicated']
variable_update = ['parameter_server', 'distributed_replicated']
max_batch_size = 64

ps = ['jingpu@140.112.90.36', 'jingpu@140.112.90.37']
worker = ['jingpu@140.112.90.36', 'jingpu@140.112.90.37']

# Device to use  as parameter server: cpu or gpu
local_parameter_device = 'gpu'

# end of address do not include '/'
remote_log_file_address = '/home/jingpu/yihong/dt-bench-log-2'
local_log_address = '/home/hong/dt-bench-log'
file_address = '/home/jingpu/benchmarks/scripts/tf_cnn_benchmarks/tf_cnn_benchmarks.py'

# if you don't need to use virtualenv, modify to ''
# virtualenv example = '/home/hong/virtialenv_dir/bin/' 
virtualenv = '~/gdr_test/bin/'

# -----------------------------------------------------------------------------------

# for batch size 1, 2, 4, 8, .....
def doubling_range(start, stop):
    while start < stop:
        yield start
        start <<=1

# result_array prepare for the excel
batch_num_array = []
for i in doubling_range(1, (max_batch_size + 1)):
	batch_num_array.append(i)
batch_num = len(batch_num_array) + 1

# data = [[None] * batch_num for i in range(len(models) +1)]
title = ['batch_size'] + models
workbook = xlsxwriter.Workbook('dt-bench.xlsx')
sheet1 = workbook.add_worksheet('parameter_server')
sheet2 = workbook.add_worksheet('distributed_replicated')  
bold = workbook.add_format({'bold': 1})

# xlsx model title and batch_size
tmp = 0			
for a in title :
	sheet1.write(tmp, 0, a)
	sheet2.write(tmp, 0, a)
	tmp += 1
tmp = 1
for b in batch_num_array :
	sheet1.write(0, tmp, b)
	sheet2.write(0, tmp, b)
	tmp += 1

# ps and worker port
ps_rand = random.randrange(10000, 30000)
worker_rand = random.randrange(1000, 5000)
ps_p = [None] * len(ps)
worker_p= [None] * len(worker)

# cmd setting
cmd_list = [None] * (len(ps) + len(worker))
cmd_kill = [None] * len(ps)
cmd_mkdir = [None] * len(worker)

# create a script to kill program
with open('kill.sh' , 'w+') as fout:
    #fout.write('nvidia-smi | awk \'$5=="' + virtualenv  +  'python" {print $3}\' | xargs kill -9\n')
    fout.write('nvidia-smi | awk \'$4=="C" {print $3}\' | xargs kill -9')
kill_cmd = ' < kill.sh'

# create remote log dir
mkdir_cmd = 'mkdir -p ' + remote_log_file_address
for c in range(len(worker)):
	cmd_mkdir[c] = 'ssh ' + worker[c] + ' \''  + mkdir_cmd + '\''
	os.system(cmd_mkdir[c])

# trans log file to localhost
cmd_trans = 'scp -r ' + worker[0] + ':' + remote_log_file_address + ' .'  

# move and rename folder
move = 'mv ' + os.path.basename(remote_log_file_address) + ' '  + os.path.dirname(local_log_address)
mv_cmd = 'mv -T ' + str(os.path.basename(remote_log_file_address)) + ' ' + str(os.path.basename(local_log_address))

# split aaa@1.1.1.1 to 1.1.1.1:80 , and combine worker and ps cmd
for i in range(len(ps)):
    ps_p[i] = ps[i].split('@')[1] + ':' + str(ps_rand)
ps_cmd = ','.join(ps_p)

for i in range(len(worker)):
    worker_p[i] = worker[i].split('@')[1] + ':' + str(worker_rand)
worker_cmd = ','.join(worker_p)

for variable in variable_update:
	for model in models: 
    		for i in doubling_range(1, (max_batch_size + 1)):
                        for a in range(len(ps)):
                            cmd_list[a] = 'ssh ' + ps[a] + ' \'' + virtualenv + \
                                          'python ' + str(file_address) + \
                                          ' --model='+ str(model) + \
                                          ' --batch_size=' + str(i) + \
                                          ' --num_gpus=' + str(gpu_number) + \
                                          ' --variable_update=' + str(variable) + \
                                          ' --job_name=ps' + \
					  ' --local_parameter_device=' + local_parameter_device + \
                                          ' --ps_hosts=' + ps_cmd  + \
                                          ' --worker_hosts=' + worker_cmd + \
                                          ' --task_index=' + str(a) + '\' &'
                        for b in range(len(worker) -1):
	                    cmd_list[len(ps)+b] ='ssh ' + worker[b] + ' \'' + virtualenv + \
                                          'python ' + str(file_address) + \
                                          ' --model='+ str(model) + \
                                          ' --batch_size=' + str(i) + \
                                          ' --num_gpus=' + str(gpu_number) + \
                                          ' --variable_update=' + str(variable) + \
                                          ' --job_name=worker' + \
					  ' --local_parameter_device=' + local_parameter_device + \
                                          ' --ps_hosts=' + ps_cmd + \
                                          ' --worker_hosts=' + worker_cmd  + \
                                          ' --task_index=' + str(b)  + \
                                          ' > ' + remote_log_file_address + '/' + str(model) + '_' + str(i) + '_' + str(variable) + '.txt\' &'
                        
                        cmd_list[len(ps)+len(worker)-1] = 'ssh ' + worker[-1] + ' \'' + ' timeout 300 ' + virtualenv + \
                                          'python ' + str(file_address) + \
                                          ' --model='+ str(model) + \
                                          ' --batch_size=' + str(i) + \
                                          ' --num_gpus=' + str(gpu_number) + \
                                          ' --variable_update=' + str(variable) + \
                                          ' --job_name=worker' + \
					  ' --local_parameter_device=' + local_parameter_device + \
                                          ' --ps_hosts=' + ps_cmd + \
                                          ' --worker_hosts=' + worker_cmd  + \
                                          ' --task_index=' + str(len(worker) -1)  + \
                                          ' > ' + remote_log_file_address + '/' + str(model) + '_' + str(i) + '_' + str(variable) + '.txt\''
                        
                        # for to execute command
                        for cmd in cmd_list :
                            print cmd
                            os.system(cmd)

                        time.sleep(20)
                       
                        # kill ps process
                        for a in range(len(ps)):
                            cmd_kill[a] = 'ssh ' + ps[a] + kill_cmd      
                        for kill in cmd_kill :
                            print kill
                            os.system(kill)

                        time.sleep(20)
                        # receive log file

# trans worker1's log file
print cmd_trans
os.system(cmd_trans)
os.remove('./kill.sh')

print move
os.system(move)
print mv_cmd
os.system(mv_cmd)

for variable in variable_update:
	for model in models: 
    		for i in doubling_range(1, (max_batch_size + 1)):
                        log_path = local_log_address + '/' + str(model) + '_' + str(i) + '_' + str(variable) + '.txt'
                        print log_path
                        if os.path.exists(log_path):
			    with open(log_path) as f:
                                if os.path.getsize(log_path) > 0:
				    txt = f.readlines()
                                
                                    if txt[-1]  != '----------------------------------------------------------------\n' :
                                        result_number = '0\n'
                                        print variable, model, i, 'img/sec : ', result_number
                                
                                    else:
        		                keys=[r for r in range(1,len(txt)+1)]

	        		        # result is dictionary that each key represent each line in output.txt
		                        result = {k:v for k,v in zip(keys,txt[::-1])}

			                # cut result to ['total images/sec', 'xx.xx']
			                result[2].split(': ') 

			                result_number = result[2].split(': ')[1] 
                                        print variable, model, i, 'img/sec : ', result_number
                                else:
                                    result_number = '0\n'
                        else:
                            result_number = '0\n'

# write the result back to excel file
			if variable == 'parameter_server' :
				sheet1.write(models.index(model)+1, batch_num_array.index(i)+1, round(float(result_number)))
			elif variable == 'distributed_replicated' :
				sheet2.write(models.index(model)+1, batch_num_array.index(i)+1, round(float(result_number)))
 
#######################################################################
#
# Create a new column chart.#
chart1 = workbook.add_chart({'type': 'column'})
chart2 = workbook.add_chart({'type': 'column'})

# Configure series. Note use of alternative syntax to define ranges.
for k in batch_num_array :
    chart1.add_series({
        'name':       ['parameter_server', 0, batch_num_array.index(k)+1],
        'categories': ['parameter_server', 1, 0, len(models), 0],
        'values':     ['parameter_server', 1, batch_num_array.index(k)+1 , len(models) , batch_num_array.index(k)+1 ],
        'data_labels': {'value': True},
                })
    chart2.add_series({
        'name':       ['distributed_replicated', 0, batch_num_array.index(k)+1],
        'categories': ['distributed_replicated', 1, 0, len(models), 0], 
        'values':     ['distributed_replicated', 1, batch_num_array.index(k)+1 , len(models) , batch_num_array.index(k)+1 ],                                                              
        'data_labels': {'value': True},
                })
 
# Add a chart title and some axis labels.
chart1.set_title ({'name': 'Variable Update Parameter_server'})
chart1.set_x_axis({'name': 'models'})
chart1.set_y_axis({'name': 'img/sec'})
 
chart2.set_title ({'name': 'Variable Update Distributed_Replicated'})
chart2.set_x_axis({'name': 'models'})
chart2.set_y_axis({'name': 'img/sec'})

# Set an Excel chart style.
chart1.set_style(11)
chart2.set_style(11) 

# Insert the chart into the worksheet (with an offset).
sheet1.insert_chart('A'+str(len(models) +5), chart1, {'x_offset': 25, 'y_offset': 10})
sheet2.insert_chart('A'+str(len(models) +5), chart2, {'x_offset': 25, 'y_offset': 10})

workbook.close()