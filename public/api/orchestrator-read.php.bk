<?php

declare(strict_types=1);

$config = require __DIR__ . '/../../app/config.php';

date_default_timezone_set($config['timezone']);
header('Content-Type: application/json; charset=UTF-8');

function sanitizeSlug(string $value): string
{
    $value = strtolower(trim($value));
    $value = preg_replace('/[^a-z0-9._-]+/', '-', $value) ?? '';
    $value = trim($value, '-._');

    return $value;
}

function normalizeProfile(array $profile, string $slug): array
{
    return [
        'slug' => $slug,
        'name' => trim((string) ($profile['name'] ?? $slug)) !== '' ? trim((string) ($profile['name'] ?? $slug)) : $slug,
        'description' => trim((string) ($profile['description'] ?? '')),
        'run' => [
            'turns' => max(1, min(40, (int) ($profile['run']['turns'] ?? 6))),
            'max_lines' => max(1, min(20, (int) ($profile['run']['max_lines'] ?? 5))),
            'max_chars' => max(50, min(4000, (int) ($profile['run']['max_chars'] ?? 500))),
            'history_depth' => max(0, min(20, (int) ($profile['run']['history_depth'] ?? 3))),
            'max_sentences' => max(1, min(12, (int) ($profile['run']['max_sentences'] ?? 4))),
        ],
        'kuzai' => [
            'label' => 'KUZAI',
            'system_prompt' => (string) ($profile['kuzai']['system_prompt'] ?? 'You are KUZAI. Reply clearly and stay concise.'),
            'temperature' => (float) ($profile['kuzai']['temperature'] ?? 0.35),
            'top_p' => (float) ($profile['kuzai']['top_p'] ?? 0.95),
            'top_k' => (int) ($profile['kuzai']['top_k'] ?? 40),
            'max_tokens' => (int) ($profile['kuzai']['max_tokens'] ?? 300),
            'repeat_penalty' => (float) ($profile['kuzai']['repeat_penalty'] ?? 1.05),
        ],
        'darkai' => [
            'label' => 'DARKAI',
            'system_prompt' => (string) ($profile['darkai']['system_prompt'] ?? 'You are DARKAI. Reply clearly and stay concise.'),
            'temperature' => (float) ($profile['darkai']['temperature'] ?? 0.35),
            'top_p' => (float) ($profile['darkai']['top_p'] ?? 0.95),
            'top_k' => (int) ($profile['darkai']['top_k'] ?? 40),
            'max_tokens' => (int) ($profile['darkai']['max_tokens'] ?? 300),
            'repeat_penalty' => (float) ($profile['darkai']['repeat_penalty'] ?? 1.05),
        ],
    ];
}

$name = isset($_GET['name']) ? (string) $_GET['name'] : '';
$slug = sanitizeSlug($name);

if ($slug === '') {
    http_response_code(422);
    echo json_encode([
        'ok' => false,
        'error' => 'Missing orchestrator name',
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

$profilesDir = $config['orchestrator']['profiles_dir'];
$file = $profilesDir . '/' . $slug . '.json';

if (!is_file($file) || !is_readable($file)) {
    http_response_code(404);
    echo json_encode([
        'ok' => false,
        'error' => 'Orchestrator not found',
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

$raw = @file_get_contents($file);
$decoded = is_string($raw) ? json_decode($raw, true) : null;

if (!is_array($decoded)) {
    http_response_code(500);
    echo json_encode([
        'ok' => false,
        'error' => 'Invalid orchestrator file',
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

$profile = normalizeProfile($decoded, $slug);

echo json_encode([
    'ok' => true,
    'profile' => $profile,
], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
