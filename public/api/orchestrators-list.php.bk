<?php

declare(strict_types=1);

$config = require __DIR__ . '/../../app/config.php';

date_default_timezone_set($config['timezone']);
header('Content-Type: application/json; charset=UTF-8');

$profilesDir = $config['orchestrator']['profiles_dir'];

if (!is_dir($profilesDir)) {
    @mkdir($profilesDir, 0775, true);
}

$items = [];
$files = glob($profilesDir . '/*.json');
if ($files === false) {
    $files = [];
}

foreach ($files as $file) {
    $slug = basename($file, '.json');
    $raw = @file_get_contents($file);
    $decoded = is_string($raw) ? json_decode($raw, true) : null;

    $items[] = [
        'slug' => $slug,
        'name' => is_array($decoded) && isset($decoded['name']) ? (string) $decoded['name'] : $slug,
        'description' => is_array($decoded) && isset($decoded['description']) ? (string) $decoded['description'] : '',
        'updated_at' => date('Y-m-d H:i:s', (int) (@filemtime($file) ?: time())),
    ];
}

usort($items, static function (array $a, array $b): int {
    return strcasecmp($a['name'], $b['name']);
});

echo json_encode([
    'ok' => true,
    'items' => $items,
    'count' => count($items),
], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
