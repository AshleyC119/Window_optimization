% ===================== 【全局优化·不陷局部最优】通信优先窗口优化 =====================
% 特点：
% 1. 全局搜索，不易陷入局部最优
% 2. 优先满足中断概率，再找“优质且足够小”的窗口
% 3. 窗口严格不出界
% 4. 比fmincon更不容易卡在糟糕的局部解
% ==============================================================================

clear; clc; close all;

%% ===================== 固定系统参数 =====================
room_x = 10;
room_y = 10;
room_z_max = 3;
n_users = 5;
sim_time = 300;
dt = 10;

params = struct();
params.E = 8;
params.d_B = 0.075;
params.x_BS = 10;
params.y_BS = -100;
params.z_BS = -10;
params.lambda = 0.075;
params.L1 = 2;
params.d_ref = abs(params.y_BS)*1.5;

params.room_x_min = 0;
params.room_x_max = room_x;
params.room_y_min = 0;
params.room_y_max = room_y;
params.room_z_min = 0;
params.room_z_max = room_z_max;

P_BS_dBm = 40;
R_th = 0.2;
N0_dBm_Hz = -174;
B = 20e6;
p_m = 1/n_users;

P_BS = 10^(P_BS_dBm/10)*1e-3;
N0 = 10^(N0_dBm_Hz/10)*1e-3 * B;
w = (1/sqrt(params.E))*ones(params.E, n_users);

%% ===================== 优化目标：优先满足中断 =====================
TARGET_OUTAGE_PROB = 0.10;   % 你要的中断上限
OUTAGE_PENALTY = 500;        % 强惩罚，保证优先满足通信

% 变量： xc, zc, Lx, Lz
lb = [0.2,  0.2,  0.1,  0.1];
ub = [room_x-0.2,  room_z_max-0.2,  room_x-0.2,  room_z_max-0.2];

nVars = 4;

%% ===================== 遗传算法（全局搜索，不陷局部最优）=====================
options_ga = optimoptions('ga', ...
    'PopulationSize', 50, ...      % 种群不大不小，速度与全局平衡
    'MaxGenerations', 100, ...     % 迭代次数适中
    'TolFun', 1e-3, ...
    'Display', 'iter', ...
    'ConstraintTolerance', 1e-3);

fprintf('=====================================================\n');
fprintf(' 启动 全局优化算法 (GA)\n');
fprintf(' 目标：满足中断 ≤ %.0f%%，并找到优质小窗口\n', TARGET_OUTAGE_PROB*100);
fprintf(' 优势：不易陷入局部最优，窗口更合理\n');
fprintf('=====================================================\n\n');

% 运行优化
[X_opt, fval, ~, exitflag] = ga(...
    @(x) obj_fun(x, params, room_x, room_z_max, n_users, sim_time, dt, P_BS, R_th, N0, p_m, w, TARGET_OUTAGE_PROB, OUTAGE_PENALTY), ...
    nVars, [], [], [], [], lb, ub, @(x) nonlcon(x, room_x, room_z_max), options_ga);

%% ===================== 结果输出 =====================
xc_opt = X_opt(1);
zc_opt = X_opt(2);
Lx_opt = X_opt(3);
Lz_opt = X_opt(4);
Area_opt = Lx_opt * Lz_opt;

final_outage = compute_average_outage(X_opt, params, room_x, room_z_max, n_users, sim_time, dt, P_BS, R_th, N0, p_m, w);

xL = xc_opt-Lx_opt/2;
xR = xc_opt+Lx_opt/2;
zD = zc_opt-Lz_opt/2;
zU = zc_opt+Lz_opt/2;

fprintf('\n\n=====================================================\n');
fprintf('✅ 全局优化完成 | 解质量更高、不易局部最优\n');
fprintf(' 窗口中心：xc=%.2f, zc=%.2f\n',xc_opt,zc_opt);
fprintf(' 窗口大小：Lx=%.2f, Lz=%.2f\n',Lx_opt,Lz_opt);
fprintf(' 窗口面积：%.3f m²\n',Area_opt);
fprintf(' 平均中断概率：%.2f%% (目标≤%.2f%%)\n',final_outage*100,TARGET_OUTAGE_PROB*100);
fprintf('-----------------------------------------------------\n');
fprintf(' 窗口边界安全：[%.2f,%.2f] × [%.2f,%.2f]\n',xL,xR,zD,zU);
fprintf('=====================================================\n');

%% ===================== 绘图 =====================
params.xc = xc_opt;
params.zc = zc_opt;
params.Lx = Lx_opt;
params.Lz = Lz_opt;
plot_coverage_map(params, room_x, room_y, P_BS, R_th, N0, p_m, w);

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% 目标函数：通信优先 + 适度最小面积
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
function cost = obj_fun(x, params, room_x, room_z_max, n_users, sim_time, dt, P_BS, R_th, N0, p_m, w, target_outage, penalty)
    xc = x(1); zc = x(2); Lx = x(3); Lz = x(4);
    area = Lx * Lz;
    outage = compute_average_outage(x, params, room_x, room_z_max, n_users, sim_time, dt, P_BS, R_th, N0, p_m, w);
    
    % 不满足中断 → 极大惩罚
    if outage > target_outage
        cost = area + penalty * (outage - target_outage)*1;
    else
        cost = area; % 满足 → 只最小化面积
    end
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% 非线性约束：窗口绝对不出界
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
function [c, ceq] = nonlcon(x, room_x, room_z_max)
    xc = x(1); zc = x(2); Lx = x(3); Lz = x(4);
    c = [
        -(xc - Lx/2);
        (xc + Lx/2) - room_x;
        -(zc - Lz/2);
        (zc + Lz/2) - room_z_max;
    ];
    ceq = [];
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% 中断概率计算（你的原版完全不变）
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
function avg_outage = compute_average_outage(x, params, room_x, room_z_max, n_users, sim_time, dt, P_BS, R_th, N0, p_m, w)
    params.xc = x(1);
    params.zc = x(2);
    params.Lx = x(3);
    params.Lz = x(4);
    [users_trajectory, users_height] = generate_human_trajectory(room_x, room_x, n_users, sim_time, dt);
    time_steps = sim_time / dt;
    total = 0;
    for user = 1:n_users
        cnt = 0;
        for step = 1:time_steps
            x = users_trajectory(user,step,1);
            y = users_trajectory(user,step,2);
            z = users_height(user);
            H = equivalent_farfield_channel_2(params,[x,y,z]);
            dp = abs(H*w(:,user))^2 * p_m * P_BS;
            intf = 0;
            for k=1:n_users
                if k~=user
                    intf = intf + abs(H*w(:,k))^2 * p_m * P_BS;
                end
            end
            sinr = dp/(intf+N0);
            rate = log2(1+sinr);
            if rate < R_th
                cnt = cnt+1;
            end
        end
        total = total + cnt/time_steps;
    end
    avg_outage = total/n_users;
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% 覆盖图
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
function plot_coverage_map(params, room_x, room_y, P_BS, R_th, N0, p_m, w)
    z_plot = 1.7;
    g = 100;
    xg = linspace(0,room_x,g);
    yg = linspace(0,room_y,g);
    map = zeros(g);
    Pth = (2^R_th-1)*N0/p_m;
    for i=1:g
        for j=1:g
            H = equivalent_farfield_channel_2(params,[xg(i),yg(j),z_plot]);
            p = abs(H*w(:,1))^2 * P_BS;
            map(j,i) = p >= Pth;
        end
    end
    figure;
    imagesc(xg,yg,map);
    colormap([0.8 0.8 0.8; 0 0.7 0]);
    xlabel('X (m)'); ylabel('Y (m)');
    title('全局优化覆盖图(绿色=正常)');
    set(gca,'YDir','normal');
    hold on;
    xw1 = params.xc-params.Lx/2;
    xw2 = params.xc+params.Lx/2;
    plot([xw1,xw2],[0,0],'r-','LineWidth',3);
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% 下面所有函数完全保留你原来的
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
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

function [H_eq] = equivalent_farfield_channel_2(params, user_pos)
    E       = params.E;
    d_B     = params.d_B;
    x_BS    = params.x_BS;
    y_BS    = params.y_BS;
    z_BS    = params.z_BS;
    xc      = params.xc;
    zc      = params.zc;
    Lx      = params.Lx;
    Lz      = params.Lz;
    lambda  = params.lambda;
    L1      = params.L1;
    d_ref   = params.d_ref;
    xu = user_pos(1); yu = user_pos(2); zu = user_pos(3);

    dx_BS = xc - x_BS; dy_BS = 0 - y_BS; dz_BS = zc - z_BS;
    R_BW  = sqrt(dx_BS^2 + dy_BS^2 + dz_BS^2);
    theta_BW  = atan2(dy_BS, dx_BS);
    phi_BW    = acos(dz_BS / R_BW);
    k_tx = sin(phi_BW) * cos(theta_BW);
    k_tz = cos(phi_BW);

    x1 = xc-Lx/2; z1=zc-Lz/2; x2=xc-Lx/2; z2=zc+Lz/2;
    x3 = xc+Lx/2; z3=zc-Lz/2; x4=xc+Lx/2; z4=zc+Lz/2;

    function [ux, uy, uz] = ray_dir(xs, zs)
        dx = xs-x_BS; dy=0-y_BS; dz=zs-z_BS; L=sqrt(dx^2+dy^2+dz^2);
        ux=dx/L; uy=dy/L; uz=dz/L;
    end

    [ux1,uy1,uz1]=ray_dir(x1,z1); [ux2,uy2,uz2]=ray_dir(x2,z2);
    [ux3,uy3,uz3]=ray_dir(x3,z3); [ux4,uy4,uz4]=ray_dir(x4,z4);

    dx_WU = xu-x_BS; dy_WU=yu-y_BS; dz_WU=zu-z_BS; L_USER=sqrt(dx_WU^2+dy_WU^2+dz_WU^2);
    ux_user=dx_WU/L_USER; uz_user=dz_WU/L_USER;

    inx = (ux_user >= min([ux1,ux2,ux3,ux4])) && (ux_user <= max([ux1,ux2,ux3,ux4]));
    inz = (uz_user >= min([uz1,uz2,uz3,uz4])) && (uz_user <= max([uz1,uz2,uz3,uz4]));
    in_illumination = inx && inz;

    dx_WU2 = xu-xc; dy_WU2=yu; dz_WU2=zu-zc; R_WU=sqrt(dx_WU2^2+dy_WU2^2+dz_WU2^2);
    t1 = dx_WU2/R_WU; t2 = dz_WU2/R_WU;

    if in_illumination
        ax=0; az=0;
    else
        ax=k_tx-t1; az=k_tz-t2;
    end

    sincx = sinc((pi/lambda)*Lx*ax);
    sincz = sinc((pi/lambda)*Lz*az);
    H = zeros(1,E);
    
    for l1=1:L1
        if l1==1
            v=(lambda/(4*pi*R_BW))*exp(-1j*(2*pi/lambda)*R_BW);
            tt=theta_BW; pt=phi_BW;
        else
            psi=2*pi*rand(); tt=-pi+2*pi*rand(); pt=pi*rand();
            eta=10^((-15+5*rand())/10);
            v=eta*(lambda/(4*pi*d_ref))*exp(-1j*psi);
        end
        n=0:E-1;
        a=(1/sqrt(E))*exp(1j*(2*pi/lambda)*d_B*n'*sin(tt));
        H=H+v*a';
    end
    
    H=sqrt(E/L1)*H;
    H_eq = H*exp(-1j*(2*pi/lambda)*(k_tx*xc+k_tz*zc))*(-1j)/(lambda*R_WU)*(Lx*Lz)*sincx*sincz;
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
