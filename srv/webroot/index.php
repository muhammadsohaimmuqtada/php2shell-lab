<?php
// "Acmecorp Cloud" — the lab's target application.
// Deliberately boring: a page that accepts POSTs and does NOT call
// session_start(). Everything interesting happens below the application,
// in PHP's request startup and shutdown.

$notice = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // No business logic worth speaking of: the form exists so POSTs have
    // somewhere to go. PHP parses the multipart body before this line runs.
    $notice = 'Thanks, our team will get back to you never.';
}
?><!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Acmecorp Cloud — enterprise synergy portal</title>
<link rel="stylesheet" href="/style.css">
</head>
<body>
<header>
  <div class="brand">ACMECORP<span>cloud</span></div>
  <nav><a href="/">Home</a><a href="/?p=about">About</a><a href="/?p=status">Status</a></nav>
</header>
<main>
  <h1>Synergy&nbsp;Portal&nbsp;2000</h1>
  <p class="tagline">Acmecorp Cloud&reg; — powered by PHP <?= PHP_VERSION ?></p>
  <?php if ($notice): ?><div class="notice"><?= htmlspecialchars($notice) ?></div><?php endif; ?>
  <form method="post" enctype="multipart/form-data" action="/">
    <label>Your name <input type="text" name="name" placeholder="Jane Doe"></label>
    <label>Feedback <textarea name="feedback" rows="3" placeholder="Tell us what to synergize"></textarea></label>
    <label>Attachment <input type="file" name="attachment"></label>
    <button type="submit">Submit feedback</button>
  </form>
  <section class="grid">
    <article><h3>99.9% uptime</h3><p>On our status page, which is also down 0.1% of the time.</p></article>
    <article><h3>Cloud native</h3><p>Runs in a container you launched five minutes ago.</p></article>
    <article><h3>Battle tested</h3><p>By you. Right now. With a multipart POST.</p></article>
  </section>
</main>
<footer><small>Acmecorp is not a real company. This server is a lab target on 127.0.0.1. Behave.</small></footer>
</body>
</html>
