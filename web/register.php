<?php
session_start();
require_once __DIR__ . '/db.php';

if (isset($_SESSION['user_id'])) {
    header('Location: index.php');
    exit;
}

$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!verify_csrf($_POST['csrf'] ?? '')) {
        $error = 'Invalid request.';
    } elseif (!rate_limit('register_' . ($_SERVER['REMOTE_ADDR'] ?? 'unknown'), 5, 3600)) {
        $error = 'Too many registration attempts. Try again in an hour.';
    } else {
        $username = trim($_POST['username'] ?? '');
        $password = $_POST['password'] ?? '';
        $confirm  = $_POST['confirm']  ?? '';

        if (!preg_match('/^[A-Za-z0-9_]{3,20}$/', $username)) {
            $error = 'Username must be 3–20 characters: letters, numbers, and underscores only.';
        } elseif (mb_strlen($password) < 8) {
            $error = 'Password must be at least 8 characters.';
        } elseif (!hash_equals($password, $confirm)) {
            $error = 'Passwords do not match.';
        } else {
            $existing = db()->prepare('SELECT id FROM users WHERE username = ?');
            $existing->execute([$username]);
            if ($existing->fetch()) {
                $error = 'That username is already taken.';
            } else {
                $hash = password_hash($password, PASSWORD_BCRYPT, ['cost' => 12]);
                db()->prepare('INSERT INTO users (username, password_hash) VALUES (?, ?)')
                    ->execute([$username, $hash]);
                $_SESSION['user_id']  = (int) db()->lastInsertId();
                $_SESSION['username'] = $username;
                header('Location: index.php');
                exit;
            }
        }
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Register — Elemental Fracture</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
<div class="panel">
  <h1>Create account</h1>

  <?php if ($error): ?>
    <p class="error"><?= htmlspecialchars($error) ?></p>
  <?php endif ?>

  <form method="post" novalidate>
    <input type="hidden" name="csrf" value="<?= csrf_token() ?>">

    <label>
      Username
      <input type="text" name="username" maxlength="20" required autofocus
             value="<?= htmlspecialchars($_POST['username'] ?? '') ?>"
             autocomplete="username">
    </label>

    <label>
      Password
      <input type="password" name="password" required autocomplete="new-password">
    </label>

    <label>
      Confirm password
      <input type="password" name="confirm" required autocomplete="new-password">
    </label>

    <button type="submit">Register</button>
  </form>

  <p class="hint">Already have an account? <a href="index.php">Sign in</a></p>
</div>
</body>
</html>
