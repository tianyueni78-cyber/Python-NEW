function export_initialization_reference(source_dir, repo_dir, output_file)
% 调用原静态QNSGA-II init.m，导出固定种子的合法性参照。
old_dir = pwd;
work_dir = tempname;
mkdir(work_dir);
cleanup = onCleanup(@() clean_work_dir(old_dir, work_dir));
cd(work_dir);
addpath(source_dir);
addpath(fullfile(source_dir, 'initial_NSGA-II'));

benchmarkRead(fullfile(source_dir, 'fjsp', 'Brandimarte_Data', 'Mk05.fjs'));
source = load('data.mat');
resource = jsondecode(fileread(fullfile(repo_dir, 'python_baseline', 'data', ...
    'resources', 'static_algorithm_comparison.json')));

machine_count = source.machineNum;
distance_matrix.load_to_machine = resource.load_to_machine(1:machine_count);
distance_matrix.machine_to_unload = resource.machine_to_unload(1:machine_count);
distance_matrix.machine_to_machine = resource.machine_to_machine(1:machine_count, 1:machine_count);
distance_matrix.load_to_unload = resource.load_to_unload;
machineEnergy.work = resource.machine_work_energy;
AGVEnergy.free = [0.6, 0.6, 0.6, 0.6];
AGVEnergy.load = [1.5, 1.5, 1.5, 1.5];

rng(20260817, 'twister');
chrom = init(100, 16.8, AGVEnergy, distance_matrix, machineEnergy, ...
    source.jobInfo, source.machineNum, 10, source.jobNum, source.operaNumVec, ...
    source.candidateMachine, 4, 4);

payload.seed = 20260817;
payload.population_size = size(chrom, 1);
payload.operation_count = sum(source.operaNumVec);
payload.chromosome_length = size(chrom, 2);
payload.chromosomes = chrom;
file_id = fopen(output_file, 'w', 'n', 'UTF-8');
fwrite(file_id, jsonencode(payload), 'char');
fclose(file_id);
end

function clean_work_dir(old_dir, work_dir)
cd(old_dir);
rmdir(work_dir, 's');
end
