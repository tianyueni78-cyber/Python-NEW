function export_brandimarte_reference(source_dir, output_dir)
% 调用原 benchmarkRead.m，为 Gate 1 生成十个 MATLAB 参照 JSON。
old_dir = pwd;
cleanup = onCleanup(@() cd(old_dir));
cd(source_dir);
if ~exist(output_dir, 'dir')
    mkdir(output_dir);
end

for index = 1:10
    name = sprintf('Mk%02d', index);
    benchmarkRead(fullfile('fjsp', 'Brandimarte_Data', [name '.fjs']));
    source = load('data.mat');

    payload.job_count = source.jobNum;
    payload.machine_count = source.machineNum;
    payload.operation_counts = source.operaNumVec;
    operations = cell(1, sum(source.operaNumVec));
    cursor = 1;
    for job_id = 1:source.jobNum
        for operation_id = 1:source.operaNumVec(job_id)
            item.job_id = job_id;
            item.operation_id = operation_id;
            item.candidate_machines = num2cell(source.candidateMachine{job_id, operation_id});
            item.processing_times = num2cell(source.jobInfo{job_id}(operation_id, source.candidateMachine{job_id, operation_id}));
            operations{cursor} = item;
            cursor = cursor + 1;
        end
    end
    payload.operations = operations;

    file_id = fopen(fullfile(output_dir, [name '.json']), 'w', 'n', 'UTF-8');
    fwrite(file_id, jsonencode(payload), 'char');
    fclose(file_id);
end
end
