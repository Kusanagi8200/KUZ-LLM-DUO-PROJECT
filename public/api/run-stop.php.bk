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

$pidFile = $config['orchestrator']['pid_file'];
$metaFile = $config['orchestrator']['meta_file'];

$pid = null;
if (is_file($pidFile)) {
    $rawPid = trim((string) @file_get_contents($pidFile));
    if ($rawPid !== '' && ctype_digit($rawPid)) {
        $pid = (int) $rawPid;
    }
}

if ($pid === null || $pid < 1) {
    http_response_code(200);
    echo json_encode([
        'ok' => true,
        'message' => 'No active run',
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

if (!is_dir('/proc/' . $pid)) {
    @unlink($pidFile);

    http_response_code(200);
    echo json_encode([
        'ok' => true,
        'message' => 'Run already finished',
        'pid' => $pid,
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

exec('kill ' . escapeshellarg((string) $pid), $output, $returnCode);
usleep(300000);

$stillRunning = is_dir('/proc/' . $pid);

if ($stillRunning) {
    exec('kill -9 ' . escapeshellarg((string) $pid), $output2, $returnCode2);
    usleep(200000);
    $stillRunning = is_dir('/proc/' . $pid);
}

if ($stillRunning) {
    http_response_code(500);
    echo json_encode([
        'ok' => false,
        'error' => 'Unable to stop run process',
        'pid' => $pid,
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

@unlink($pidFile);

$meta = [];
if (is_file($metaFile) && is_readable($metaFile)) {
    $decoded = json_decode((string) @file_get_contents($metaFile), true);
    if (is_array($decoded)) {
        $meta = $decoded;
    }
}

$meta['status'] = 'stopped';
$meta['stopped_at'] = date('Y-m-d H:i:s');
$meta['stopped_pid'] = $pid;

@file_put_contents(
    $metaFile,
    json_encode($meta, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES)
);

http_response_code(200);
echo json_encode([
    'ok' => true,
    'message' => 'Run stopped',
    'pid' => $pid,
], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
