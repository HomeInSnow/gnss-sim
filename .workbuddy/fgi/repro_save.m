
% repro_save.m -- minimal repro: who holds a classdef object?
addpath(genpath('D:/workbuddy/GNSSSignal/gnss-sim/.workbuddy/fgi/shim'));
addpath(genpath('D:/workbuddy/GNSSSignal/gnss-sim/FGI-GSRx-2.1.3'), '-begin');
cd('D:/workbuddy/GNSSSignal/gnss-sim/FGI-GSRx-2.1.3/param');
settings = readSettings('D:/workbuddy/GNSSSignal/gnss-sim/.workbuddy/fgi/param_gnsssim_fgi.txt');
acqData  = doAcquisition(settings);
printf('acq done\n');
try
  save('-v6', 'D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/t_settings.mat', 'settings');
  disp('settings OK');
catch e
  printf('settings FAIL: %s\n', e.message);
end
try
  save('-v6', 'D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/t_acq.mat', 'acqData');
  disp('acqData OK');
catch e
  printf('acqData FAIL: %s\n', e.message);
end
% scan acqData for objects
scan_obj(acqData, 'acqData');

disp('done')
