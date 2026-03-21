<?php

declare(strict_types=1);

$config = require __DIR__ . '/../../app/config.php';

date_default_timezone_set($config['timezone']);
header('Content-Type: application/json; charset=UTF-8');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode([
        'ok' => false,
        'error' => 'Method not allowed',
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function sanitizeSlug(string $value): string
{
    $value = strtolower(trim($value));
    $value = preg_replace('/[^a-z0-9._-]+/', '-', $value) ?? '';
    $value = trim($value, '-._');

    return $value;
}

$rawInput = file_get_contents('php://input');
$data = json_decode($rawInput ?: '', true);

if (!is_array($data)) {
    http_response_code(400);
    echo json_encode([
        'ok' => false,
        'error' => 'Invalid JSON body',
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

$openingPrompt = trim((string) ($data['opening_prompt'] ?? ''));
$orchestratorName = sanitizeSlug((string) ($data['orchestrator_name'] ?? ''));

if ($openingPrompt === '') {
    http_response_code(422);
    echo json_encode([
        'ok' => false,
        'error' => 'Opening prompt is required',
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

if ($orchestratorName === '') {
    http_response_code(422);
    echo json_encode([
        'ok' => false,
        'error' => 'Orchestrator name is required',
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

$pythonBin = $config['orchestrator']['python_bin'];
$scriptPath = $config['orchestrator']['script_path'];
$outputDir = $config['orchestrator']['output_dir'];
$launcherDir = $config['orchestrator']['launcher_dir'];
$pidFile = $config['orchestrator']['pid_file'];
$metaFile = $config['orchestrator']['meta_file'];
$profilesDir = $config['orchestrator']['profiles_dir'];
$profileFile = $profilesDir . '/' . $orchestratorName . '.json';

if (!is_dir($launcherDir) && !@mkdir($launcherDir, 0775, true)) {
    http_response_code(500);
    echo json_encode([
        'ok' => false,
        'error' => 'Unable to create launcher directory',
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

if (!is_dir($outputDir) && !@mkdir($outputDir, 0775, true)) {
    http_response_code(500);
    echo json_encode([
        'ok' => false,
        'error' => 'Unable to create output directory',
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

if (!is_executable($pythonBin)) {
    http_response_code(500);
    echo json_encode([
        'ok' => false,
        'error' => 'Python binary is not executable: ' . $pythonBin,
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

if (!is_file($scriptPath)) {
    http_response_code(500);
    echo json_encode([
        'ok' => false,
        'error' => 'Orchestrator engine not found: ' . $scriptPath,
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

if (!is_file($profileFile)) {
    http_response_code(404);
    echo json_encode([
        'ok' => false,
        'error' => 'Selected orchestrator profile not found',
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

$existingPid = null;
if (is_file($pidFile)) {
    $rawPid = trim((string) @file_get_contents($pidFile));
    if ($rawPid !== '' && ctype_digit($rawPid)) {
        $existingPid = (int) $rawPid;
    }
}

if ($existingPid !== null && $existingPid > 0 && is_dir('/proc/' . $existingPid)) {
    http_response_code(409);
    echo json_encode([
        'ok' => false,
        'error' => 'A run is already in progress',
        'pid' => $existingPid,
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

$timestamp = date('Ymd-His');
$stdoutFile = $launcherDir . '/run-' . $timestamp . '.stdout.log';
$stderrFile = $launcherDir . '/run-' . $timestamp . '.stderr.log';

$command = implode(' ', [
    'nohup',
    escapeshellarg($pythonBin),
    escapeshellarg($scriptPath),
    '--profile-file',
    escapeshellarg($profileFile),
    '--opening-prompt',
    escapeshellarg($openingPrompt),
    '--output-dir',
    escapeshellarg($outputDir),
    '>',
    escapeshellarg($stdoutFile),
    '2>',
    escapeshellarg($stderrFile),
    '&',
    'echo',
    '$!',
]);

$output = [];
$returnCode = 0;
exec($command, $output, $returnCode);

$pid = null;
if (isset($output[0])) {
    $pidRaw = trim((string) $output[0]);
    if ($pidRaw !== '' && ctype_digit($pidRaw)) {
        $pid = (int) $pidRaw;
    }
}

if ($returnCode !== 0 || $pid === null || $pid < 1) {
    http_response_code(500);
    echo json_encode([
        'ok' => false,
        'error' => 'Unable to start orchestrator process',
        'return_code' => $returnCode,
        'output' => $output,
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

@file_put_contents($pidFile, (string) $pid);

$meta = [
    'pid' => $pid,
    'status' => 'running',
    'started_at' => date('Y-m-d H:i:s'),
    'opening_prompt' => $openingPrompt,
    'orchestrator_name' => $orchestratorName,
    'profile_file' => $profileFile,
    'stdout_file' => $stdoutFile,
    'stderr_file' => $stderrFile,
    'output_dir' => $outputDir,
];

@file_put_contents(
    $metaFile,
    json_encode($meta, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES)
);

http_response_code(200);
echo json_encode([
    'ok' => true,
    'message' => 'Run started',
    'pid' => $pid,
    'started_at' => $meta['started_at'],
    'orchestrator_name' => $orchestratorName,
], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
