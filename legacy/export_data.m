clear; clc;

sim_time_long = 2000; % 跑长一点的时间，让统计规律更准
dt = 10;
n_users = 5;
room_x = 10;
room_y = 10;

fprintf('正在生成长周期的用户运动轨迹，请稍候...\n');

% 调用原有的轨迹生成函数
[users_trajectory, users_height] = generate_human_trajectory(room_x, room_y, n_users, sim_time_long, dt);

time_steps = sim_time_long / dt;
total_rows = n_users * time_steps;

% 预分配内存，防止大数据卡顿
total_points = zeros(total_rows, 3);

row_idx = 1;
for user = 1:n_users
    for step = 1:time_steps
        X = users_trajectory(user, step, 1);
        Y = users_trajectory(user, step, 2);
        Z = users_height(user);

        total_points(row_idx, :) = [X, Y, Z];
        row_idx = row_idx + 1;
    end
end

% 使用 writematrix 导出
filename = 'human_meta_trajectory.csv';
writematrix(total_points, filename);

fprintf('=====================================================\n');
fprintf('✅ 成功导出 %d 个用户空间轨迹点！\n', size(total_points, 1));
fprintf('📁 文件已保存在当前目录下，文件名: %s\n', filename);
fprintf('=====================================================\n');


function [users_trajectory, users_height] = generate_human_trajectory(room_x, room_y, n_users, sim_time, dt)
    positions = getHumanPosi_custom(room_x, room_y, n_users, sim_time, dt);
    users_trajectory = positions;
    users_height = 1.5 + 0.5 * rand(n_users, 1);
end

function positions = getHumanPosi_custom(room_x, room_y, n_users, sim_time, dt)
    room_size = [0, room_x, 0, room_y];
    hotspot_center = [room_x/2, room_y/2];
    hotspot_radius = room_x/3;
    p_t = 0.6;  p_s = 0.3;  tau_h = 1.5;  tau_n = 0.1;
    v_h = 0.2;  v_n = 1.0;  g_h = 0.6;  g_n = 0.2;
    time_steps = sim_time / dt;
    users = struct();
    for i = 1:n_users
        users(i).pos = [room_size(1)+rand()*(room_size(2)-room_size(1)), room_size(3)+rand()*(room_size(4)-room_size(3))];
        dist2hot = norm(users(i).pos - hotspot_center);
        if dist2hot <= hotspot_radius
            users(i).region = 'hot' ;
        else
            users(i).region = 'normal';
        end
        if rand < p_t
            users(i).state = 'transfer';
            users(i).target = generate_target_pos_custom(users(i).pos, hotspot_center, hotspot_radius, g_h, g_n, room_size);
            dir_vec = users(i).target - users(i).pos;
            users(i).dir = dir_vec / norm(dir_vec);
            users(i).speed = get_speed_custom(users(i).region, v_h, v_n);
        else
            users(i).state = 'pause';
            users(i).pause_remain = exprnd(get_tau_custom(users(i).region, tau_h, tau_n));
        end
        users(i).trajectory = zeros(time_steps, 2);
        users(i).trajectory(1, :) = users(i).pos;
    end
    for step = 2:time_steps
        for i = 1:n_users
            if users(i).state == "pause"
                users(i).pause_remain = users(i).pause_remain - dt;
                users(i).trajectory(step, :) = users(i).pos;
                if users(i).pause_remain <= 0
                    users(i).state = 'transfer';
                    users(i).target = generate_target_pos_custom(users(i).pos, hotspot_center, hotspot_radius, g_h, g_n, room_size);
                    dir_vec = users(i).target - users(i).pos;
                    users(i).dir = dir_vec / norm(dir_vec);
                    users(i).speed = get_speed_custom(users(i).region, v_h, v_n);
                end
            else
                move_dist = users(i).speed * dt;
                pos_diff = users(i).target - users(i).pos;
                if norm(pos_diff) <= move_dist
                    users(i).pos = users(i).target;
                    dist2hot = norm(users(i).pos - hotspot_center);
                    if dist2hot <= hotspot_radius
                        users(i).region = 'hot' ;
                    else
                        users(i).region = 'normal';
                    end
                    if rand < p_s
                        users(i).state = 'pause';
                        users(i).pause_remain = exprnd(get_tau_custom(users(i).region, tau_h, tau_n));
                    else
                        users(i).target = generate_target_pos_custom(users(i).pos, hotspot_center, hotspot_radius, g_h, g_n, room_size);
                        dir_vec = users(i).target - users(i).pos;
                        users(i).dir = dir_vec / norm(dir_vec);
                        users(i).speed = get_speed_custom(users(i).region, v_h, v_n);
                    end
                else
                    users(i).pos = users(i).pos + users(i).dir * move_dist;
                end
                users(i).trajectory(step, :) = users(i).pos;
            end
        end
    end
    positions = zeros(n_users, time_steps, 2);
    for i = 1:n_users
        positions(i,:,:) = users(i).trajectory;
    end
end

function target = generate_target_pos_custom(current_pos, hc, hr, gh, gn, rs)
    if rand < gh
        target = hc + (rand(1,2)-0.5)*2*hr;
    else
        target = [rs(1)+rand()*(rs(2)-rs(1)), rs(3)+rand()*(rs(3))+rand()*(rs(4)-rs(3))];
    end
    target(1) = max(min(target(1), rs(2)), rs(1));
    target(2) = max(min(target(2), rs(4)), rs(3));
end

function tau = get_tau_custom(region, tau_h, tau_n)
    tau = strcmp(region,'hot')*tau_h + strcmp(region,'normal')*tau_n;
end

function speed = get_speed_custom(region, v_h, v_n)
    speed = strcmp(region,'hot')*v_h + strcmp(region,'normal')*v_n;
end