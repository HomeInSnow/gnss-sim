% run_fgi.m -- non-interactive Octave driver for FGI-GSRx 2.1.3 on the
% gnss-sim replica of the Aalto 2024 thesis 6.2 Skydel scenario.
%
% Usage:
%   octave --no-gui --eval "run('D:/workbuddy/GNSSSignal/gnss-sim/.workbuddy/fgi/run_fgi.m')"

root = 'D:/workbuddy/GNSSSignal/gnss-sim/FGI-GSRx-2.1.3';

% gsrx.m starts with "clearvars -except varargin", which wipes the base
% workspace -> keep our configuration in globals (clearvars leaves them).
global FGI_PARAMFILE FGI_OUTMAT
if isempty(FGI_PARAMFILE)
  FGI_PARAMFILE = 'D:/workbuddy/GNSSSignal/gnss-sim/.workbuddy/fgi/param_gnsssim_fgi.txt';
end
if isempty(FGI_OUTMAT)
  FGI_OUTMAT    = 'D:/workbuddy/GNSSSignal/gnss-sim/out/fgi/fgi_results.mat';
end

% shim dir FIRST (Octave lacks contains() used by gsrx.m)
addpath(genpath('D:/workbuddy/GNSSSignal/gnss-sim/.workbuddy/fgi/shim'));
% make sure every FGI folder (and subfolder) is on the load path
addpath(genpath(root), '-begin');
addpath(genpath('D:/workbuddy/GNSSSignal/gnss-sim/.workbuddy/fgi/shim'), '-begin');

% readParamFile opens 'defaultReceiverConfiguration.txt' cwd-relative
cd(fullfile(root, 'param'));

% gsrx.m is a script: its results land in this (base) workspace
gsrx(FGI_PARAMFILE);

unames   = who();
keep     = {'settings','acqData','ephData','trackData','obsData','navData','statResults'};
savevars = keep(ismember(keep, unames));
odir = fileparts(FGI_OUTMAT);
if exist(odir, 'dir') ~= 7
  mkdir(odir);
end
save('-v6', FGI_OUTMAT, savevars{:});
printf('FGI_RUN_OK saved %d vars to %s\n', numel(savevars), FGI_OUTMAT);
