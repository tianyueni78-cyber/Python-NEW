% Verification-only exporter for Step 7. It does not modify algorithm behavior.
clear;
clc;

script_dir = fileparts(mfilename('fullpath'));
repo_dir = fileparts(fileparts(script_dir));
source_root = fileparts(repo_dir);
algorithm_root = fullfile(source_root, '第2篇代码 - 静态算法对比');

objectives = [
    1, 5;
    2, 4;
    3, 3;
    4, 2;
    5, 1;
    3, 5;
    5, 5;
    2, 4;
    3, 4;
    4, 4
];
population_size = 4;

addpath(fullfile(algorithm_root, 'initial_NSGA-II'));
qnsga_sorted = non_domination(objectives, 0, 2);
rmpath(fullfile(algorithm_root, 'initial_NSGA-II'));

addpath(fullfile(algorithm_root, 'NSGA-II'));
nsga_ranked = non_domination(objectives, 0, 2);
nsga_elite = replace_chrom(nsga_ranked, 0, 2, population_size);
rmpath(fullfile(algorithm_root, 'NSGA-II'));

% Fixed tournament candidates isolate rank/crowding comparison from RNG parity.
candidate_pairs = [1, 6; 2, 3; 4, 5; 2, 8; 7, 9];
tournament_winners = zeros(size(candidate_pairs, 1), 1);
for i = 1:size(candidate_pairs, 1)
    pair = candidate_pairs(i, :);
    pair_rows = qnsga_sorted(pair, :);
    minimum_rank = min(pair_rows(:, 3));
    eligible = find(pair_rows(:, 3) == minimum_rank);
    if length(eligible) == 1
        winner_in_pair = eligible(1);
    else
        maximum_distance = max(pair_rows(eligible, 4));
        distance_ties = eligible(pair_rows(eligible, 4) == maximum_distance);
        winner_in_pair = distance_ties(1);
    end
    tournament_winners(i) = pair(winner_in_pair);
end

% Fixed IPOX/MPX and mutation inputs use two legal Mk05 chromosomes.
initialization_path = fullfile(repo_dir, 'python_baseline', 'data', ...
    'matlab_reference', 'Mk05_initialization_seed_20260817.json');
initialization = jsondecode(fileread(initialization_path));
parent_1 = initialization.chromosomes(1, :);
parent_2 = initialization.chromosomes(2, :);
operation_count = initialization.operation_count;
selected_jobs = [1, 3, 5];
selected_rs_positions = [1, 4, 10, 100, 200, 300, 400];

parent_1_os = parent_1(1:operation_count);
parent_2_os = parent_2(1:operation_count);
parent_1_rs = parent_1(operation_count+1:end);
parent_2_rs = parent_2(operation_count+1:end);
selected_1 = ismember(parent_1_os, selected_jobs);
selected_2 = ismember(parent_2_os, selected_jobs);
child_1_os = parent_1_os .* ~selected_1;
child_1_os(child_1_os == 0) = parent_2_os(selected_2);
child_2_os = parent_2_os .* ~selected_2;
child_2_os(child_2_os == 0) = parent_1_os(selected_1);
child_2_rs = parent_1_rs;
child_1_rs = parent_2_rs;
child_1_rs(selected_rs_positions) = parent_1_rs(selected_rs_positions);
child_2_rs(selected_rs_positions) = parent_2_rs(selected_rs_positions);
crossover_children = [child_1_os, child_2_rs; child_2_os, child_1_rs];

mutation_os_positions = [1, 2];
mutation_rs_positions = [2, 50, 150];
mutation_rs_values = parent_2_rs(mutation_rs_positions);
mutated_child = crossover_children(1, :);
mutated_child(mutation_os_positions) = ...
    mutated_child(fliplr(mutation_os_positions));
mutated_child(operation_count + mutation_rs_positions) = mutation_rs_values;

reference = struct();
reference.description = '第7步MATLAB固定目标矩阵参考';
reference.objectives = objectives;
reference.population_size = population_size;
reference.qnsga_sorted_infinite = isinf(qnsga_sorted);
qnsga_sorted(isinf(qnsga_sorted)) = 0;
reference.qnsga_sorted = qnsga_sorted;
qnsga_elite = qnsga_sorted(1:population_size, :);
reference.qnsga_elite = qnsga_elite;
reference.nsga_ranked_infinite = isinf(nsga_ranked);
nsga_ranked(isinf(nsga_ranked)) = 0;
reference.nsga_ranked = nsga_ranked;
reference.nsga_elite_infinite = isinf(nsga_elite);
nsga_elite(isinf(nsga_elite)) = 0;
reference.nsga_elite = nsga_elite;
reference.candidate_pairs = candidate_pairs;
reference.tournament_winners_matlab_1_based = tournament_winners;
reference.genetic_parent_rows = [parent_1; parent_2];
reference.selected_jobs_matlab_1_based = selected_jobs;
reference.selected_rs_positions_matlab_1_based = selected_rs_positions;
reference.crossover_children = crossover_children;
reference.mutation_os_positions_matlab_1_based = mutation_os_positions;
reference.mutation_rs_positions_matlab_1_based = mutation_rs_positions;
reference.mutation_rs_values_matlab_1_based = mutation_rs_values;
reference.mutated_child = mutated_child;

output_path = fullfile(repo_dir, 'python_baseline', 'data', ...
    'matlab_reference', 'multiobjective_step7.json');
fid = fopen(output_path, 'w');
if fid == -1
    error('Cannot open output file: %s', output_path);
end
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, '%s', jsonencode(reference, PrettyPrint=true));
fprintf('Wrote %s\n', output_path);
