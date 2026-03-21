<?php

declare(strict_types=1);

return [
    'app_name' => 'KUZCHAT LLM DUO',
    'app_env' => 'production',
    'timezone' => 'Europe/Paris',

    'nodes' => [
        'kuzai' => [
            'label' => 'KUZAI',
            'host' => 'fhc2',
            'ip' => '10.141.52.19',
            'role' => 'Node A',
            'api_base' => 'http://10.141.52.19:8080',
            'chat_endpoint' => 'http://10.141.52.19:8080/v1/chat/completions',
            'models_endpoint' => 'http://10.141.52.19:8080/v1/models',
            'theme_class' => 'kuzai',
        ],
        'darkai' => [
            'label' => 'DARKAI',
            'host' => 'fhc',
            'ip' => '10.141.52.126',
            'role' => 'Node B',
            'api_base' => 'http://10.141.52.126:8080',
            'chat_endpoint' => 'http://10.141.52.126:8080/v1/chat/completions',
            'models_endpoint' => 'http://10.141.52.126:8080/v1/models',
            'theme_class' => 'darkai',
        ],
    ],

    'ui' => [
        'theme' => 'kuz-neon-blue',
        'brand_line' => 'THE KUZ NETWORK // KUZAI.ORG',
        'subtitle' => 'DUO ORCHESTRATION CONSOLE',
        'poll_interval_ms' => 5000,
    ],

    'orchestrator' => [
        'python_bin' => '/opt/llm/orchestrator/venv/bin/python3',
        'script_path' => '/opt/llm/orchestrator/duo_loop_engine.py',
        'profiles_dir' => '/var/www/html/KUZCHAT-LLM-DUO/storage/orchestrators',
        'output_dir' => '/var/www/html/KUZCHAT-LLM-DUO/storage/runs',
        'launcher_dir' => '/var/www/html/KUZCHAT-LLM-DUO/storage/launcher',
        'pid_file' => '/var/www/html/KUZCHAT-LLM-DUO/storage/launcher/current_run.pid',
        'meta_file' => '/var/www/html/KUZCHAT-LLM-DUO/storage/launcher/current_run.json',
    ],
];
