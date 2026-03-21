<?php

declare(strict_types=1);

$config = require __DIR__ . '/../../app/config.php';

date_default_timezone_set($config['timezone']);

header('Content-Type: application/json; charset=UTF-8');

function readTextFileSafe(string $path): ?string
{
    if (!is_readable($path)) {
        return null;
    }

    $content = @file_get_contents($path);
    if ($content === false) {
        return null;
    }

    return trim($content);
}

function readHostname(): string
{
    $hostname = readTextFileSafe('/etc/hostname');
    if ($hostname !== null && $hostname !== '') {
        return $hostname;
    }

    return php_uname('n');
}

function readUptimeSeconds(): ?int
{
    $raw = readTextFileSafe('/proc/uptime');
    if ($raw === null || $raw === '') {
        return null;
    }

    $parts = preg_split('/\s+/', $raw);
    if (!isset($parts[0]) || !is_numeric($parts[0])) {
        return null;
    }

    return (int) floor((float) $parts[0]);
}

function formatUptime(?int $seconds): string
{
    if ($seconds === null || $seconds < 0) {
        return 'unknown';
    }

    $days = intdiv($seconds, 86400);
    $seconds %= 86400;
    $hours = intdiv($seconds, 3600);
    $seconds %= 3600;
    $minutes = intdiv($seconds, 60);

    $parts = [];

    if ($days > 0) {
        $parts[] = $days . 'd';
    }

    if ($hours > 0) {
        $parts[] = $hours . 'h';
    }

    $parts[] = $minutes . 'm';

    return implode(' ', $parts);
}

function readMemoryInfo(): array
{
    $result = [
        'total_mb' => null,
        'available_mb' => null,
        'used_mb' => null,
        'used_percent' => null,
    ];

    $raw = readTextFileSafe('/proc/meminfo');
    if ($raw === null) {
        return $result;
    }

    $data = [];
    foreach (explode("\n", $raw) as $line) {
        if (preg_match('/^([A-Za-z_]+):\s+(\d+)\s+kB$/', trim($line), $matches)) {
            $data[$matches[1]] = (int) $matches[2];
        }
    }

    if (!isset($data['MemTotal'], $data['MemAvailable'])) {
        return $result;
    }

    $totalKb = $data['MemTotal'];
    $availableKb = $data['MemAvailable'];
    $usedKb = $totalKb - $availableKb;

    $result['total_mb'] = (int) round($totalKb / 1024);
    $result['available_mb'] = (int) round($availableKb / 1024);
    $result['used_mb'] = (int) round($usedKb / 1024);

    if ($totalKb > 0) {
        $result['used_percent'] = round(($usedKb / $totalKb) * 100, 1);
    }

    return $result;
}

function readLoadAverage(): ?string
{
    $raw = readTextFileSafe('/proc/loadavg');
    if ($raw === null || $raw === '') {
        return null;
    }

    $parts = preg_split('/\s+/', $raw);
    if (count($parts) < 3) {
        return null;
    }

    return $parts[0] . ' / ' . $parts[1] . ' / ' . $parts[2];
}

function httpJson(string $url, int $timeoutSeconds = 4): array
{
    $ch = curl_init($url);

    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => false,
        CURLOPT_CONNECTTIMEOUT => $timeoutSeconds,
        CURLOPT_TIMEOUT => $timeoutSeconds,
        CURLOPT_HTTPHEADER => [
            'Accept: application/json',
        ],
    ]);

    $start = microtime(true);
    $body = curl_exec($ch);
    $latencyMs = (int) round((microtime(true) - $start) * 1000);

    $errno = curl_errno($ch);
    $error = $errno !== 0 ? curl_error($ch) : null;
    $status = (int) curl_getinfo($ch, CURLINFO_RESPONSE_CODE);

    curl_close($ch);

    if ($errno !== 0) {
        return [
            'ok' => false,
            'http_code' => $status,
            'latency_ms' => $latencyMs,
            'error' => $error,
            'data' => null,
        ];
    }

    if ($body === false || $body === '') {
        return [
            'ok' => false,
            'http_code' => $status,
            'latency_ms' => $latencyMs,
            'error' => 'Empty response body',
            'data' => null,
        ];
    }

    $decoded = json_decode($body, true);

    if (!is_array($decoded)) {
        return [
            'ok' => false,
            'http_code' => $status,
            'latency_ms' => $latencyMs,
            'error' => 'Invalid JSON response',
            'data' => null,
        ];
    }

    return [
        'ok' => $status >= 200 && $status < 300,
        'http_code' => $status,
        'latency_ms' => $latencyMs,
        'error' => null,
        'data' => $decoded,
    ];
}

function extractModelName(?array $payload): ?string
{
    if ($payload === null) {
        return null;
    }

    if (isset($payload['data'][0]['id']) && is_string($payload['data'][0]['id'])) {
        return $payload['data'][0]['id'];
    }

    if (isset($payload['models'][0]['name']) && is_string($payload['models'][0]['name'])) {
        return $payload['models'][0]['name'];
    }

    return null;
}

function tcpReachable(string $host, int $port, float $timeoutSeconds = 2.0): array
{
    $errno = 0;
    $errstr = '';

    $start = microtime(true);
    $fp = @fsockopen($host, $port, $errno, $errstr, $timeoutSeconds);
    $latencyMs = (int) round((microtime(true) - $start) * 1000);

    if (is_resource($fp)) {
        fclose($fp);

        return [
            'ok' => true,
            'latency_ms' => $latencyMs,
            'error' => null,
        ];
    }

    return [
        'ok' => false,
        'latency_ms' => $latencyMs,
        'error' => trim($errstr) !== '' ? $errstr : 'Connection failed',
    ];
}

$kuzaiModels = httpJson($config['nodes']['kuzai']['models_endpoint']);
$darkaiModels = httpJson($config['nodes']['darkai']['models_endpoint']);
$darkaiTcp = tcpReachable($config['nodes']['darkai']['ip'], 8080);

$memory = readMemoryInfo();
$uptimeSeconds = readUptimeSeconds();

$response = [
    'app' => [
        'name' => $config['app_name'],
        'timestamp' => date('Y-m-d H:i:s'),
        'php_version' => PHP_VERSION,
        'apache_hint' => $_SERVER['SERVER_SOFTWARE'] ?? 'unknown',
    ],
    'system' => [
        'hostname' => readHostname(),
        'server_ip' => $_SERVER['SERVER_ADDR'] ?? $config['nodes']['kuzai']['ip'],
        'load_average' => readLoadAverage(),
        'uptime' => formatUptime($uptimeSeconds),
        'memory' => $memory,
    ],
    'nodes' => [
        'kuzai' => [
            'label' => $config['nodes']['kuzai']['label'],
            'host' => $config['nodes']['kuzai']['host'],
            'ip' => $config['nodes']['kuzai']['ip'],
            'api_base' => $config['nodes']['kuzai']['api_base'],
            'models_endpoint' => $config['nodes']['kuzai']['models_endpoint'],
            'reachable' => $kuzaiModels['ok'],
            'http_code' => $kuzaiModels['http_code'],
            'latency_ms' => $kuzaiModels['latency_ms'],
            'model_name' => extractModelName($kuzaiModels['data']),
            'error' => $kuzaiModels['error'],
        ],
        'darkai' => [
            'label' => $config['nodes']['darkai']['label'],
            'host' => $config['nodes']['darkai']['host'],
            'ip' => $config['nodes']['darkai']['ip'],
            'api_base' => $config['nodes']['darkai']['api_base'],
            'models_endpoint' => $config['nodes']['darkai']['models_endpoint'],
            'reachable' => $darkaiModels['ok'],
            'http_code' => $darkaiModels['http_code'],
            'latency_ms' => $darkaiModels['latency_ms'],
            'model_name' => extractModelName($darkaiModels['data']),
            'error' => $darkaiModels['error'],
            'tcp_8080' => $darkaiTcp,
        ],
    ],
    'checks' => [
        'web_php' => true,
        'kuzai_models_api' => $kuzaiModels['ok'],
        'darkai_models_api' => $darkaiModels['ok'],
        'fhc2_to_fhc_tcp_8080' => $darkaiTcp['ok'],
    ],
];

http_response_code(200);
echo json_encode($response, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
