<?php
session_start();
require_once __DIR__ . '/db.php';

$error = '';
$token = '';
$user  = null;

// ── Logout ────────────────────────────────────────────────────────────────────
if (isset($_GET['logout'])) {
    session_destroy();
    header('Location: index.php');
    exit;
}

// ── Load session user ─────────────────────────────────────────────────────────
if (isset($_SESSION['user_id'])) {
    $stmt = db()->prepare('SELECT * FROM users WHERE id = ?');
    $stmt->execute([$_SESSION['user_id']]);
    $user = $stmt->fetch() ?: null;
    if (!$user) {
        session_destroy();
        header('Location: index.php');
        exit;
    }
}

// ── POST handling ─────────────────────────────────────────────────────────────
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? '';

    if (!verify_csrf($_POST['csrf'] ?? '')) {
        $error = 'Invalid request.';

    } elseif ($action === 'login' && !$user) {
        if (!rate_limit('login_' . ($_SERVER['REMOTE_ADDR'] ?? 'unknown'), 10, 300)) {
            $error = 'Too many login attempts. Wait 5 minutes.';
        } else {
            $username = trim($_POST['username'] ?? '');
            $password = $_POST['password'] ?? '';
            $stmt = db()->prepare('SELECT * FROM users WHERE username = ?');
            $stmt->execute([$username]);
            $row = $stmt->fetch();
            if ($row && password_verify($password, $row['password_hash'])) {
                $_SESSION['user_id']  = $row['id'];
                $_SESSION['username'] = $row['username'];
                header('Location: index.php');
                exit;
            }
            // Constant-time fallback to prevent timing attacks on username enumeration
            password_verify('dummy', '$2y$12$invalidhashpadding000000000000000000000000000000000000');
            $error = 'Invalid username or password.';
        }

    } elseif ($action === 'token' && $user) {
        if (!rate_limit('token_' . $user['id'], 20, 3600)) {
            $error = 'Too many token requests. Try again later.';
        } else {
            $tok = generate_token(16);
            // Invalidate any existing unused token for this user, then insert the new one
            db()->prepare('DELETE FROM tokens WHERE user_id = ? AND used_at IS NULL')
                ->execute([$user['id']]);
            db()->prepare('INSERT INTO tokens (user_id, token) VALUES (?, ?)')
                ->execute([$user['id'], $tok]);
            $token = $tok;
        }
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Elemental Fracture</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
<div class="panel">

<?php if (!$user): ?>
  <!-- ── Login ── -->
  <h1>Sign in</h1>

  <?php if ($error): ?>
    <p class="error"><?= htmlspecialchars($error) ?></p>
  <?php endif ?>

  <form method="post" novalidate>
    <input type="hidden" name="csrf"   value="<?= csrf_token() ?>">
    <input type="hidden" name="action" value="login">

    <label>
      Username
      <input type="text" name="username" required autofocus autocomplete="username">
    </label>

    <label>
      Password
      <input type="password" name="password" required autocomplete="current-password">
    </label>

    <button type="submit">Sign in</button>
  </form>

  <p class="hint">No account? <a href="register.php">Register</a></p>

<?php else: ?>
  <!-- ── Dashboard ── -->
  <h1>Welcome, <?= htmlspecialchars($user['username']) ?></h1>

  <?php if ($error): ?>
    <p class="error"><?= htmlspecialchars($error) ?></p>
  <?php endif ?>

  <?php if ($token): ?>
  <div class="token-box">
    <p>Paste this as your in-game name to join:</p>
    <code id="tok"><?= htmlspecialchars($token) ?></code>
    <button type="button" onclick="navigator.clipboard.writeText(document.getElementById('tok').textContent)">Copy</button>
    <p class="hint">Single-use. Generate a new token each time you want to connect.</p>
  </div>
  <?php endif ?>

  <form method="post">
    <input type="hidden" name="csrf"   value="<?= csrf_token() ?>">
    <input type="hidden" name="action" value="token">
    <button type="submit">Generate join token</button>
  </form>

  <p class="hint"><a href="?logout=1">Sign out</a></p>
<?php endif ?>

</div>
</body>
</html>
