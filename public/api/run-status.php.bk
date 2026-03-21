<?php

declare(strict_types=1);

$config = require __DIR__ . '/../../app/config.php';

date_default_timezone_set($config['timezone']);
header('Content-Type: application/json; charset=UTF-8');

function readJsonFileSafe(string $path): ?array
{
    if (!is_file($path) || !is_readable($path)) {
        return null;
    }

    $raw = @file_get_contents($path);
    if ($raw === false || trim($raw) === '') {
        return null;
    }

    $decoded = json_decode($raw, true);
    return is_array($decoded) ? $decoded : null;
}

function writeJsonFileSafe(string $path, array $data): void
{
    @file_put_contents(
        $path,
        json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES)
    );
}

function tailFileSafe(string $path, int $maxLines = 20): array
{
    if (!is_file($path) || !is_readable($path)) {
        return [];
    }

    $lines = @file($path, FILE_IGNORE_NEW_LINES);
    if (!is_array($lines)) {
        return [];
    }

    return array_slice($lines, -$maxLines);
}

function findLatestRun(string $runsDir): ?array
{
    if (!is_dir($runsDir)) {
        return null;
    }

    $entries = scandir($runsDir);
    if (!is_array($entries)) {
        return null;
    }

    $dirs = [];
    foreach ($entries as $entry) {
        if ($entry === '.' || $entry === '..') {
            continue;
        }

        $fullPath = $runsDir . '/' . $entry;
        if (is_dir($fullPath) && str_starts_with($entry, 'run-ab-')) {
            $dirs[] = [
                'name' => $entry,
                'path' => $fullPath,
                'mtime' => @filemtime($fullPath) ?: 0,
            ];
        }
    }

    if ($dirs === []) {
        return null;
    }

    usort($dirs, static function (array $a, array $b): int {
        return $b['mtime'] <=> $a['mtime'];
    });

    return $dirs[0];
}

function readTranscriptEntries(string $runDir): array
{
    $transcriptPath = $runDir . '/transcript.json';
    $decoded = readJsonFileSafe($transcriptPath);

    if (!is_array($decoded)) {
        return [];
    }

    $entries = [];
    foreach ($decoded as $item) {
        if (!is_array($item)) {
            continue;
        }

        $entries[] = [
            'turn' => isset($item['turn']) ? (int) $item['turn'] : 0,
            'speaker' => (string) ($item['speaker'] ?? ''),
            'content' => (string) ($item['content'] ?? ''),
            'timestamp' => (string) ($item['timestamp'] ?? ''),
        ];
    }

    return $entries;
}

$pidFile = $config['orchestrator']['pid_file'];
$metaFile = $config['orchestrator']['meta_file'];
$runsDir = $config['orchestrator']['output_dir'];

$meta = readJsonFileSafe($metaFile);
$latestRun = findLatestRun($runsDir);

$pid = null;
if (is_file($pidFile)) {
    $rawPid = trim((string) @file_get_contents($pidFile));
    if ($rawPid !== '' && ctype_digit($rawPid)) {
        $pid = (int) $rawPid;
    }
}

$isRunning = $pid !== null && $pid > 0 && is_dir('/proc/' . $pid);

$transcript = [];
$latestRunInfo = null;

if ($latestRun !== null) {
    $transcript = readTranscriptEntries($latestRun['path']);
    $latestRunInfo = [
        'name' => $latestRun['name'],
        'path' => $latestRun['path'],
        'mtime' => date('Y-m-d H:i:s', (int) $latestRun['mtime']),
        'transcript_json' => is_file($latestRun['path'] . '/transcript.json')
            ? $latestRun['path'] . '/transcript.json'
            : null,
        'transcript_md' => is_file($latestRun['path'] . '/transcript.md')
            ? $latestRun['path'] . '/transcript.md'
            : null,
    ];
}

$status = 'idle';
$note = 'No run launched yet.';
$stdoutTail = [];
$stderrTail = [];

if ($meta !== null) {
    $stdoutFile = (string) ($meta['stdout_file'] ?? '');
    $stderrFile = (string) ($meta['stderr_file'] ?? '');

    if ($stdoutFile !== '') {
        $stdoutTail = tailFileSafe($stdoutFile, 30);
    }

    if ($stderrFile !== '') {
        $stderrTail = tailFileSafe($stderrFile, 30);
    }
}

if ($isRunning) {
    $status = 'running';
    $note = 'A Duo run is currently in progress.';

    if ($meta !== null && ($meta['status'] ?? '') !== 'running') {
        $meta['status'] = 'running';
        writeJsonFileSafe($metaFile, $meta);
    }
} elseif ($meta !== null && $latestRunInfo !== null && count($transcript) > 0) {
    $status = 'completed';
    $note = 'The last Duo run completed successfully.';
    @unlink($pidFile);

    $meta['status'] = 'completed';
    if (!isset($meta['completed_at'])) {
        $meta['completed_at'] = date('Y-m-d H:i:s');
    }
    $meta['latest_run'] = $latestRunInfo['name'];
    writeJsonFileSafe($metaFile, $meta);
} elseif ($meta !== null && (($meta['status'] ?? '') === 'stopped')) {
    $status = 'stopped';
    $note = 'The last Duo run was stopped manually.';
    @unlink($pidFile);
    writeJsonFileSafe($metaFile, $meta);
} elseif ($meta !== null && $stderrTail !== []) {
    $status = 'failed';
    $note = 'The last run ended with an error.';
    @unlink($pidFile);

    $meta['status'] = 'failed';
    if (!isset($meta['completed_at'])) {
        $meta['completed_at'] = date('Y-m-d H:i:s');
    }
    writeJsonFileSafe($metaFile, $meta);
} elseif ($meta !== null) {
    $status = 'finished';
    $note = 'The process ended. Waiting for transcript files or completion state.';
    @unlink($pidFile);

    $meta['status'] = 'finished';
    if (!isset($meta['completed_at'])) {
        $meta['completed_at'] = date('Y-m-d H:i:s');
    }
    writeJsonFileSafe($metaFile, $meta);
} elseif ($latestRunInfo !== null && count($transcript) > 0) {
    $status = 'completed';
    $note = 'A previous Duo run transcript is available.';
}

http_response_code(200);
echo json_encode([
    'ok' => true,
    'status' => $status,
    'note' => $note,
    'active' => $meta,
    'is_running' => $isRunning,
    'pid' => $isRunning ? $pid : null,
    'latest_run' => $latestRunInfo,
    'transcript' => $transcript,
    'stdout_tail' => $stdoutTail,
    'stderr_tail' => $stderrTail,
    'timestamp' => date('Y-m-d H:i:s'),
], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
