function export_ablation_reference()
% 第10步验证脚本：从锁定的四个MATLAB入口导出消融特征。
script_dir = fileparts(mfilename('fullpath'));
repo_root = fileparts(fileparts(script_dir));
source_root = fullfile(fileparts(repo_root), '第2篇代码 - 静态算法对比');

entries = {
    'A', fullfile(source_root, 'NSGA-II', 'NSGA2.m');
    'B', fullfile(source_root, 'Multi-NSGA-II', 'initial_INSGA_II.m');
    'C', fullfile(source_root, 'QNSGA-II', 'initial_INSGA_II.m');
    'full', fullfile(source_root, 'initial_NSGA-II', 'initial_INSGA_II.m')
};

for i = 1:size(entries, 1)
    name = entries{i, 1};
    text = fileread(entries{i, 2});
    item.name = name;
    item.random_initialization = contains(text, 'chrom = init(pop, jobNum');
    item.hybrid_initialization = contains(text, 'chrom = init(AGVEG_MAX');
    item.initial_nondomination_sort = contains(text, ...
        "chrom = non_domination(chrom, dim, obj_num);");
    item.has_local_search = contains(text, 'vns_ = VNS(');
    item.neighborhood_count = 0;
    if contains(text, "{'N1','N2','N3','N4','N5','N6'}")
        item.neighborhood_count = 6;
    end
    item.random_action = contains(text, ...
        'action = randperm(numel(option_), 1)');
    item.q_action = contains(text, '[~,action] = max(Qtable(currt_State,:))');
    item.q_update = contains(text, ...
        'Qtable(currt_State,action)=Qtable(currt_State,action)+');
    item.generation_stop = contains(text, 'while gen < max_gen');
    item.cpu_time_stop = contains(text, 'while toc(tstart) < max_time');
    reference.variants.(name) = item;
end

reference.locked_order = {'A', 'B', 'C', 'full'};
reference.fair_python_stop = 'same_generations';
out_file = fullfile(repo_root, 'python_baseline', 'data', ...
    'matlab_reference', 'ablations_step10.json');
fid = fopen(out_file, 'w');
fprintf(fid, '%s', jsonencode(reference, PrettyPrint=true));
fclose(fid);
end
