function export_comparators_reference()
% 第9步验证脚本：导出三种对比算法公共机制的固定MATLAB参考。
script_dir = fileparts(mfilename('fullpath'));
repo_root = fileparts(fileparts(script_dir));
source_root = fileparts(repo_root);
moead_dir = fullfile(source_root, '第2篇代码 - 静态算法对比', 'MOEAD');
addpath(moead_dir);

lambda = generateLamda(5, 2);
neighbor = get_neighbor(lambda, 2);
objective_min = [10, 20];
fit = [14, 26];
chebyshev = zeros(5, 1);
for i = 1:5
    chebyshev(i) = compare(fit, i, lambda, objective_min);
end

chrom = [zeros(5, 2), [14 28; 13 29; 12 30; 16 25; 11 33]];
offspring = [zeros(1, 2), 12, 27];
updated = update_neighbor(chrom, neighbor(3, :), offspring, lambda, objective_min, 2);

job_num = 3;
operation_counts = [2, 1, 2];
candidate_counts = [2, 3, 1, 2, 4];
agv_num = 3;
speed_num = 4;
position = [-2.8, 1.2, -0.5, 2.9, 0.1, -3, -1, 0, 1, 3, ...
            -2.5, -0.2, 2.5, -1.5, 1.5, -3, -2, -1, 0, 1, 2, 3, -2.2, 2.2, -0.8];
os_real = position(1:5);
base_os = [1, 1, 2, 3, 3];
[~, up_index] = sort(os_real);
[~, os_index] = sort(up_index);
os = base_os(os_index);
ms_real = position(6:10);
as_real = position(11:15);
ss_real = position(16:25);
ms = zeros(1, 5);
as = zeros(1, 5);
ss = zeros(1, 10);
for i = 1:5
    ms(i) = round((ms_real(i) + job_num) / (2 * job_num) * (candidate_counts(i) - 1) + 1);
    as(i) = round((as_real(i) + job_num) / (2 * job_num) * (agv_num - 1) + 1);
    ss(2*i-1) = round((ss_real(2*i-1) + job_num) / (2 * job_num) * (speed_num - 1) + 1);
    ss(2*i) = round((ss_real(2*i) + job_num) / (2 * job_num) * (speed_num - 1) + 1);
end

fitness = [1 4; 2 3; 3 2; 4 1; 2 4];
dominated = check_domination_reference(fitness);

reference.lambda = lambda;
reference.neighbor = neighbor;
reference.objective_min = objective_min;
reference.fit = fit;
reference.chebyshev = chebyshev;
reference.update_neighbor_input = chrom;
reference.update_neighbor_offspring = offspring;
reference.update_neighbor_indices = neighbor(3, :);
reference.update_neighbor_output = updated;
reference.mopso.position = position;
reference.mopso.operation_counts = operation_counts;
reference.mopso.candidate_counts = candidate_counts;
reference.mopso.agv_num = agv_num;
reference.mopso.speed_num = speed_num;
reference.mopso.chromosome = [os, ms, as, ss];
reference.mopso.dominance_objectives = fitness;
reference.mopso.dominated = dominated;

out_file = fullfile(repo_root, 'python_baseline', 'data', 'matlab_reference', 'comparators_step9.json');
fid = fopen(out_file, 'w');
fprintf(fid, '%s', jsonencode(reference, PrettyPrint=true));
fclose(fid);
end

function dom_vector = check_domination_reference(fitness)
count = size(fitness, 1);
dom_vector = zeros(count, 1);
all_perm = nchoosek(1:count, 2);
all_perm = [all_perm; [all_perm(:,2), all_perm(:,1)]];
d = all(fitness(all_perm(:,1),:) <= fitness(all_perm(:,2),:), 2) & ...
    any(fitness(all_perm(:,1),:) < fitness(all_perm(:,2),:), 2);
dom_vector(unique(all_perm(d == 1, 2))) = 1;
end
