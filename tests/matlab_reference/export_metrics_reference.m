function export_metrics_reference(repo_root)
% 第12步验证专用：固定两组目标，调用论文主线指标函数导出参考。
if nargin < 1
    repo_root = fileparts(fileparts(fileparts(mfilename('fullpath'))));
end
source_root = fileparts(repo_root);
metric_root = fullfile(source_root, '第2篇代码 - 静态算法对比');
addpath(fullfile(metric_root, 'HV'));
addpath(fullfile(metric_root, 'IGD'));
addpath(fullfile(metric_root, 'Spacing'));
addpath(fullfile(source_root, '第2篇代码 - 静态自身策略对比', 'C-metric'));
A = [1,4;2,2;4,1];
B = [1.5,3.5;3,1.5];
all_points = [A;B];
lo = min(all_points, [], 1);
hi = max(all_points, [], 1);
An = (A-lo)./(hi-lo);
Bn = (B-lo)./(hi-lo);
front = [An;Bn];
keep = true(size(front,1),1);
for i=1:size(front,1)
    for j=1:size(front,1)
        if i~=j && all(front(j,:)<=front(i,:)) && any(front(j,:)<front(i,:))
            keep(i)=false; break
        end
    end
end
front = unique(front(keep,:), 'rows', 'stable');
ref.instance = 'fixed_two_groups';
ref.groups = {A,B};
ref.normalized = {An,Bn};
ref.reference_front = front;
ref.hv = [test_lebesgue_measure(An,[1.1;1.1]), test_lebesgue_measure(Bn,[1.1;1.1])];
ref.igd = [IGD_compution(front,An), IGD_compution(front,Bn)];
% 原Spacing.m仅用pdist2计算cityblock距离；验证脚本展开同一公式，避免工具箱依赖。
ref.spacing = [spacing_without_toolbox(An),spacing_without_toolbox(Bn)];
ref.c_ab = c_compute_A_B(An,Bn);
ref.c_ba = c_compute_A_B(Bn,An);
target = fullfile(repo_root,'python_baseline','data','matlab_reference','metrics_step12.json');
fid=fopen(target,'w'); cleanup=onCleanup(@() fclose(fid));
fprintf(fid,'%s',jsonencode(ref));
end

function score=spacing_without_toolbox(points)
n=size(points,1); nearest=inf(n,1);
for i=1:n
    for j=1:n
        if i~=j
            nearest(i)=min(nearest(i),sum(abs(points(i,:)-points(j,:))));
        end
    end
end
score=std(nearest);
end
