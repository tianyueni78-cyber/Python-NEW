% Verification-only Step 8 exporter. Original MATLAB sources stay unchanged.
clear;
clc;

script_dir = fileparts(mfilename('fullpath'));
repo_dir = fileparts(fileparts(script_dir));
source_root = fileparts(repo_dir);
source_dir = fullfile(source_root, '第2篇代码 - 静态算法对比');
algorithm_dir = fullfile(source_dir, 'initial_NSGA-II');
old_dir = pwd;
work_dir = tempname;
mkdir(work_dir);
cleanup = onCleanup(@() clean_work_dir(old_dir, work_dir));
cd(work_dir);
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

strategies = {'N1', 'N2', 'N3', 'N4', 'N5', 'N6'};
results = cell(1, numel(strategies));
for action = 1:numel(strategies)
    rng(20260817 + action, 'twister');
    entry.strategy = strategies{action};
    entry.seed = 20260817 + action;
    try
        output = VNS(chrom, source.jobNum, source.jobInfo, source.operaNumVec, ...
            machine_count, 4, AGVSpeed, source.candidateMachine, distance_matrix, ...
            machineEnergy, AGVEnergy, 100, 16.8, 20, 2, strategies{action});
        entry.success = true;
        entry.chromosome = output(1:5 * sum(source.operaNumVec));
        entry.objectives = output(end-1:end);
        entry.error_identifier = '';
        entry.error_message = '';
    catch exception
        entry.success = false;
        entry.chromosome = [];
        entry.objectives = [];
        entry.error_identifier = exception.identifier;
        entry.error_message = exception.message;
    end
    results{action} = entry;
end

objectives = [1, 5; 2, 4; 3, 3; 4, 2; 5, 1; 3, 5];
time_median = median(objectives(:, 1));
energy_median = median(objectives(:, 2));
states = zeros(size(objectives, 1), 1);
for index = 1:size(objectives, 1)
    if objectives(index, 1) <= time_median
        states(index) = 1 + (objectives(index, 2) > energy_median);
    else
        states(index) = 3 + (objectives(index, 2) > energy_median);
    end
end
old_objective = [3, 4];
new_objectives = [2, 3; 4, 5; 2, 5];
maximum = [5, 5];
minimum = [1, 1];
rewards = zeros(size(new_objectives, 1), 1);
for index = 1:size(new_objectives, 1)
    normalized = sum((maximum - new_objectives(index, :)) ./ (maximum - minimum));
    if all(new_objectives(index, :) < old_objective)
        rewards(index) = 2 + normalized;
    elseif all(new_objectives(index, :) > old_objective)
        rewards(index) = 0;
    else
        rewards(index) = 1 + normalized;
    end
end
qtable = zeros(4, 6);
qtable(2, :) = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6];
alpha = 0.1;
gamma = 0.9;
current_state = 1;
action = 3;
next_state = 2;
reward = rewards(1);
qtable(current_state, action) = qtable(current_state, action) + alpha * (...
    reward + gamma * max(qtable(next_state, :)) - qtable(current_state, action));

payload.instance = 'Mk05';
payload.chromosome = chrom;
payload.neighborhoods = results;
payload.state_objectives = objectives;
payload.time_median = time_median;
payload.energy_median = energy_median;
payload.states = states;
payload.reward_old_objective = old_objective;
payload.reward_new_objectives = new_objectives;
payload.reward_maximum = maximum;
payload.reward_minimum = minimum;
payload.rewards = rewards;
payload.updated_qtable = qtable;

output_path = fullfile(repo_dir, 'python_baseline', 'data', ...
    'matlab_reference', 'qnsga_step8.json');
file_id = fopen(output_path, 'w', 'n', 'UTF-8');
fwrite(file_id, jsonencode(payload, PrettyPrint=true), 'char');
fclose(file_id);
fprintf('Wrote %s\n', output_path);

function clean_work_dir(old_dir, work_dir)
cd(old_dir);
rmdir(work_dir, 's');
end
