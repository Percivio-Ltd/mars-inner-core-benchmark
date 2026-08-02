% Production driver for the frozen UCLA_v4 Octave route.
% Inputs and output locations are supplied by run_ucla_octave.sh via the
% environment.  The extracted archive is disposable and lives in WORKDIR.

input_path = getenv('UCLA_INPUT_PATH');
output_path = getenv('UCLA_OUTPUT_PATH');
work_dir = getenv('UCLA_WORK_DIR');
archive_dir = getenv('UCLA_ARCHIVE_DIR');
driver_dir = getenv('UCLA_DRIVER_DIR');

if isempty(input_path) || isempty(output_path) || isempty(work_dir) || ...
   isempty(archive_dir) || isempty(driver_dir)
  error('UCLA-DRIVER-FAIL: required UCLA_* environment variable is missing');
end
if exist(input_path, 'file') ~= 2
  error('UCLA-DRIVER-FAIL: input does not exist: %s', input_path);
end
if exist(archive_dir, 'dir') ~= 7
  error('UCLA-DRIVER-FAIL: extracted archive directory does not exist: %s', archive_dir);
end

pkg load signal
pkg load control
addpath(driver_dir, '-begin');  % demonstrated pause() no-op shim
set(0, 'defaultfigurevisible', 'off');
cd(archive_dir);

fixture = load('Conservative.mat');
if ~isfield(fixture, 'Conservative') || fixture.Conservative ~= 0
  error('UCLA-DRIVER-FAIL: shipped Conservative fixture is not zero');
end

printf('UCLA-DRIVER: octave=%s input=%s\n', version(), input_path);
t0 = tic;
file = input_path;

% Shipped MAIN2SPS body.  It calls rdmseed(file,'plot'), selects the exact
% 02:BHU/V/W channels using XseedDataFDS, calls funcadjustTimes, runs all
% three 2-sps detection branches, includes MAIN20SPSReconcile, and performs
% the second cclim=0.4 pass.  Plots are invisible and pause() is a no-op.
MAIN2SPS

post1 = exist('Data', 'var') && iscell(Data) && numel(Data) == 3 && ...
        exist('times', 'var') && iscell(times) && numel(times) == 3 && ...
        exist('freq', 'var') && freq == 20 && ...
        exist('aaout', 'var') && exist('I1P', 'var') && exist('G1P', 'var');
if ~post1
  error('UCLA-DRIVER-FAIL: MAIN2SPS postconditions failed');
end
channel_lengths = cellfun(@numel, Data(:));
time_lengths = cellfun(@numel, times(:));
if any(channel_lengths <= 0) || any(channel_lengths ~= time_lengths)
  error('UCLA-DRIVER-FAIL: selected channel data/time lengths are invalid');
end
if any(channel_lengths ~= channel_lengths(1))
  error('UCLA-DRIVER-FAIL: funcadjustTimes did not produce equal channel lengths');
end
printf('UCLA-DRIVER: aligned samples U/V/W = %d/%d/%d at %.1f s\n', ...
       channel_lengths(1), channel_lengths(2), channel_lengths(3), toc(t0));

% Shipped MAIN20SPSJuly26 body.  Conservative=0 selects the shipped
% PREP08/PREP03/PREP39 competition; pauses and visible plots are neutralized.
MAIN20SPSJuly26

post2 = exist('dc', 'var') && iscell(dc) && numel(dc) == 3 && ...
        exist('aaout3', 'var') && iscell(aaout3) && numel(aaout3) == 3 && ...
        all(cellfun(@numel, dc(:)) == channel_lengths) && ...
        all(cellfun(@(m) size(m, 1), aaout3(:)) > 0);
if ~post2
  error('UCLA-DRIVER-FAIL: MAIN20SPSJuly26 postconditions failed');
end
close all;

results_path = fullfile(work_dir, 'ucla_results.mat');
octave_version = version();
elapsed = toc(t0);
save('-v7', results_path, 'dc', 'aaout3', 'Data', 'times', 'freq', ...
     'channel_lengths', 'elapsed', 'octave_version');

parts_dir = fullfile(work_dir, 'ucla_mseed_parts');
if exist(parts_dir, 'dir') == 7
  error('UCLA-DRIVER-FAIL: MiniSEED parts directory already exists: %s', parts_dir);
end
mkdir(parts_dir);

channel_names = {'BHU', 'BHV', 'BHW'};
part_bases = cell(1, 3);
for ch = 1:3
  part_bases{ch} = fullfile(parts_dir, ...
      sprintf('XB.ELYSE.02.%s.D', channel_names{ch}));
  % dc is double, so the shipped mkmseed default is IEEE float64 encoding 5.
  mkmseed(part_bases{ch}, dc{ch}, times{ch}, 20);
end

partial_output = fullfile(work_dir, 'ucla_output.partial.mseed');
if exist(partial_output, 'file') == 2
  error('UCLA-DRIVER-FAIL: partial output already exists: %s', partial_output);
end
out_fid = fopen(partial_output, 'wb');
if out_fid < 0
  error('UCLA-DRIVER-FAIL: cannot open partial output: %s', partial_output);
end

part_count = 0;
try
  % Byte concatenation in U, V, W order, matching PREPmkmseed.m's !cat flow.
  for ch = 1:3
    part_files = sort(glob(fullfile(parts_dir, ...
        sprintf('XB.ELYSE.02.%s.*', channel_names{ch}))));
    if isempty(part_files)
      error('UCLA-DRIVER-FAIL: mkmseed wrote no files for %s', channel_names{ch});
    end
    for pi = 1:numel(part_files)
      in_fid = fopen(part_files{pi}, 'rb');
      if in_fid < 0
        error('UCLA-DRIVER-FAIL: cannot read MiniSEED part: %s', part_files{pi});
      end
      bytes = fread(in_fid, Inf, '*uint8');
      fclose(in_fid);
      if fwrite(out_fid, bytes, 'uint8') ~= numel(bytes)
        error('UCLA-DRIVER-FAIL: short write while concatenating: %s', part_files{pi});
      end
      part_count = part_count + 1;
    end
  end
  fclose(out_fid);
catch err
  fclose(out_fid);
  rethrow(err);
end

if part_count < 3
  error('UCLA-DRIVER-FAIL: expected at least three MiniSEED parts, got %d', part_count);
end
if exist(output_path, 'file') == 2
  error('UCLA-DRIVER-FAIL: refusing to overwrite output: %s', output_path);
end
[move_ok, move_msg] = movefile(partial_output, output_path);
if ~move_ok
  error('UCLA-DRIVER-FAIL: cannot move output into place: %s', move_msg);
end

n_rows = cellfun(@(m) size(m, 1), aaout3(:));
printf('UCLA-DRIVER-PASS: rows U/V/W=%d/%d/%d elapsed=%.1f output=%s\n', ...
       n_rows(1), n_rows(2), n_rows(3), elapsed, output_path);
