function export_dynamic_reference(repo_root)
% 第11步验证专用：从已锁定Mk05 MATLAB时间表导出固定动态事件状态。
if nargin < 1
    repo_root = fileparts(fileparts(fileparts(mfilename('fullpath'))));
end
source = fullfile(repo_root, 'python_baseline', 'data', 'matlab_reference', ...
    'Mk05_decoder_reference.json');
raw = jsondecode(fileread(source));
event_time = 100;
completed = 0;
in_process = 0;
total = 0;
for m = 1:numel(raw.machine_tables)
    table = raw.machine_tables{m};
    for k = 1:numel(table)
        block = table(k);
        if block.job == 0
            continue
        end
        total = total + 1;
        if block.end <= event_time
            completed = completed + 1;
        elseif block.start < event_time && event_time < block.end
            in_process = in_process + 1;
        end
    end
end
reference.instance = 'Mk05';
reference.event_time = event_time;
reference.completed_operations = completed;
reference.in_process_operations = in_process;
reference.remaining_operations = total - completed;
reference.machine_failure = struct('target', 3, 'duration', 20);
reference.agv_failure = struct('target', 1, 'duration', 15);
reference.order_cancellation = struct('target', 4);
reference.strategy_semantics = struct( ...
    'IS', 'initial_*: no variation', ...
    'RS', 'event-constrained rescheduling', ...
    'CS', 'CRS_*: complete rescheduling');
target = fullfile(repo_root, 'python_baseline', 'data', 'matlab_reference', ...
    'dynamic_step11.json');
fid = fopen(target, 'w');
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, '%s', jsonencode(reference));
end
