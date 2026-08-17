function export_decoder_reference(source_dir, repo_dir, output_file)
% 对固定Mk05染色体调用原sorting/fitness，导出Gate 3逐层参照。
old_dir = pwd;
work_dir = tempname;
mkdir(work_dir);
cleanup = onCleanup(@() clean_work_dir(old_dir, work_dir));
cd(work_dir);
algorithm_dir = fullfile(source_dir, 'initial_NSGA-II');
addpath(source_dir);
addpath(algorithm_dir);

benchmarkRead(fullfile(source_dir, 'fjsp', 'Brandimarte_Data', 'Mk05.fjs'));
source = load('data.mat');
resource = jsondecode(fileread(fullfile(repo_dir, 'python_baseline', 'data', ...
    'resources', 'static_algorithm_comparison.json')));
initialization = jsondecode(fileread(fullfile(repo_dir, 'python_baseline', 'data', ...
    'matlab_reference', 'Mk05_initialization_seed_20260817.json')));
chrom = initialization.chromosomes(1, :);

machine_count = source.machineNum;
distance_matrix.load_to_machine = resource.load_to_machine(1:machine_count);
distance_matrix.machine_to_unload = resource.machine_to_unload(1:machine_count);
distance_matrix.machine_to_machine = resource.machine_to_machine(1:machine_count, 1:machine_count);
distance_matrix.load_to_unload = resource.load_to_unload;
machineEnergy.work = resource.machine_work_energy;
machineEnergy.free = resource.machine_idle_energy;
AGVSpeed = [1.0, 1.0, 1.0, 1.0];
AGVEnergy.free = [0.6, 0.6, 0.6, 0.6];
AGVEnergy.load = [1.5, 1.5, 1.5, 1.5];

work.start = 0; work.end = Inf; work.job = 0; work.opera = 0;
for index = 1:machine_count
    machineTable{index} = work;
end
transfer.start = 0; transfer.end = Inf; transfer.job = 0; transfer.opera = 0;
transfer.load_status = 0; transfer.from_machine = -1; transfer.to_machine = 0; transfer.charge = 0;
for index = 1:4
    AGVTable{index} = transfer;
end
[machineTable, AGVTable, jobCompletion, batteryRecords, chargeCounts] = sorting( ...
    chrom, source.jobNum, source.jobInfo, source.operaNumVec, 4, AGVSpeed, ...
    source.candidateMachine, distance_matrix, AGVEnergy, 100, 16.8, 20, ...
    machineTable, AGVTable);
[func, ~, ~, makespan, machineEnergyTotal, agvEnergyTotal] = fitness( ...
    chrom, source.jobNum, source.jobInfo, source.operaNumVec, machine_count, 4, ...
    AGVSpeed, source.candidateMachine, distance_matrix, machineEnergy, AGVEnergy, ...
    100, 16.8, 20);

payload.instance = 'Mk05';
payload.chromosome_matlab_1_based = chrom;
payload.objectives = func{1};
payload.makespan = makespan;
payload.machine_energy = machineEnergyTotal;
payload.agv_energy = agvEnergyTotal;
payload.job_completion = jobCompletion;
payload.charge_counts = chargeCounts;
payload.machine_tables = machineTable;
payload.agv_tables = AGVTable;
payload.battery_records = batteryRecords;
file_id = fopen(output_file, 'w', 'n', 'UTF-8');
fwrite(file_id, jsonencode(payload), 'char');
fclose(file_id);
end

function clean_work_dir(old_dir, work_dir)
cd(old_dir);
rmdir(work_dir, 's');
end
