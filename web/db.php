<?php
/**
 * Shared database helpers. Both PHP and Python point at the same elefrac.db file.
 * DB_PATH is relative to the repo root (one level up from web/).
 */

define('DB_PATH', dirname(__DIR__) . '/elefrac.db');

function db(): PDO {
    static $pdo = null;
    if ($pdo === null) {
        $pdo = new PDO('sqlite:' . DB_PATH, null, null, [
            PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ]);
        $pdo->exec('PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;');
    }
    return $pdo;
}

/**
 * Generate a random token using an unambiguous character set.
 * Default length 16 matches the proxy's expected token length.
 */
function generate_token(int $length = 16): string {
    $chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789';
    $token = '';
    for ($i = 0; $i < $length; $i++) {
        $token .= $chars[random_int(0, strlen($chars) - 1)];
    }
    return $token;
}

function csrf_token(): string {
    if (empty($_SESSION['csrf'])) {
        $_SESSION['csrf'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf'];
}

function verify_csrf(string $token): bool {
    return isset($_SESSION['csrf']) && hash_equals($_SESSION['csrf'], $token);
}

/**
 * Simple sliding-window rate limiter backed by the rate_limits table.
 * Returns true if the action is allowed, false if the limit is exceeded.
 */
function rate_limit(string $key, int $max, int $window_secs): bool {
    $now = time();
    $pdo = db();
    $pdo->exec(
        "CREATE TABLE IF NOT EXISTS rate_limits (
            key    TEXT    NOT NULL,
            hit_at INTEGER NOT NULL
        )"
    );
    $pdo->prepare('DELETE FROM rate_limits WHERE hit_at < ?')->execute([$now - $window_secs]);
    $count = (int) $pdo->prepare('SELECT COUNT(*) FROM rate_limits WHERE key = ?')
                       ->execute([$key])
                       ->fetchColumn();
    if ($count >= $max) {
        return false;
    }
    $pdo->prepare('INSERT INTO rate_limits (key, hit_at) VALUES (?, ?)')->execute([$key, $now]);
    return true;
}
