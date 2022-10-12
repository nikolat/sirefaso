<?php
date_default_timezone_set('Asia/Tokyo');
if (!file_exists('./repos/')) {
    mkdir('./repos');
}
$dl = true;
$search_key = 'sirefaso';
$search_url = 'https://api.github.com/search/repositories?q=topic:'. $search_key. '&sort=updated';
$next_filename = 'repos0.txt';
if ($dl) {
    download_file($search_url, 'repos/'. $next_filename);
}
$data_repos = [];
$c = 0;
while ($next_filename != '') {
    $lines = file(__DIR__. '/repos/'. $next_filename, FILE_IGNORE_NEW_LINES);
    $next_filename = '';
    $header_end = false;
    foreach ($lines as $line) {
        if (preg_match('/<(.+?)>; rel="next"/', $line, $matches)) {
            $next_url = $matches[1];
            $next_filename = 'repos'. ($c + 1). '.txt';
            if ($dl) {
                download_file($next_url, 'repos/'. $next_filename);
            }
            $json = file_get_contents(__DIR__. '/repos/'. $next_filename);
            if ($json === false) {
                throw new \RuntimeException('file not found.');
            }
        }
        elseif ($header_end) {
            $json = $line;
            $data_repos[$c] = json_decode($json, true);
            $c++;
            break;
        }
        elseif ($line === '') {
            $header_end = true;
        }
    }
}
$repos = [];
$c = 0;
$n = 30;
$date_now = strtotime('now');
for ($j = 0; $j < count($data_repos); $j++) {
    for ($i = 0; $i < $n; $i++) {
        if (!isset($data_repos[$j]['items'][$i])) {
            break;
        }
        $item = $data_repos[$j]['items'][$i];
        if (!isset($item['topics'])) {
            continue;
        }
        $topics = $item['topics'];
        $type = '';
        if (in_array('ukagaka-ghost', $topics)) {
            $type = 'ghost';
        }
        elseif (in_array('ukagaka-shell', $topics)) {
            $type = 'shell';
        }
        elseif (in_array('ukagaka-balloon', $topics)) {
            $type = 'balloon';
        }
        elseif (in_array('ukagaka-plugin', $topics)) {
            $type = 'plugin';
        }
        elseif (in_array('ukagaka-supplement', $topics)) {
            $type = 'supplement';
        }
        elseif (in_array('ukagaka-shiori', $topics)) {
            $type = 'shiori';
        }
        elseif (in_array('ukagaka-saori', $topics)) {
            $type = 'saori';
        }
        elseif (in_array('ukagaka-tool', $topics)) {
            $type = 'tool';
        }
        elseif (in_array('ukagaka-spec', $topics)) {
            $type = 'spec';
        }
        else {
            continue;
        }
        $date_update = strtotime($item['pushed_at']);
        $diff = $date_now - $date_update;
        $classname = '';
        if ($diff < 1 * 24 * 60 * 60) {
            $classname = 'days-over-0';
        }
        else if ($diff < 7 * 24 * 60 * 60) {
            $classname = 'days-over-1';
        }
        else if ($diff < 30 * 24 * 60 * 60) {
            $classname = 'days-over-7';
        }
        else if ($diff < 365 * 24 * 60 * 60) {
            $classname = 'days-over-30';
        }
        else {
            $classname = 'days-over-365';
        }
        $repo = [
            'id' => str_replace('/', '_', $item['full_name']),
            'title' => $item['name'],
            'category' => $type,
            'classname' => $classname,
            'author' => $item['owner']['login'],
            'html_url' => $item['html_url'],
            'created_at_time' => $item['created_at'],
            'created_at_str' => date("Y-m-d H:i:s", strtotime($item['created_at'])),
            'updated_at_time' => $item['pushed_at'],
            'updated_at_str' => date("Y-m-d H:i:s", strtotime($item['pushed_at']))
        ];
        $repos[$c] = $repo;
        $c++;
    }
}
function download_file($url, $filename)
{
    $ch = curl_init($url);
    $fp = fopen($filename, 'w');
    curl_setopt($ch, CURLOPT_FILE, $fp);
    curl_setopt($ch, CURLOPT_HEADER, true);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/1.0 (Win3.1)');
    curl_exec($ch);
    if(curl_error($ch)) {
        fwrite($fp, curl_error($ch));
    }
    curl_close($ch);
    fclose($fp);
}
function s($s)
{
    return htmlspecialchars($s, ENT_QUOTES | ENT_SUBSTITUTE | ENT_HTML401);
}
?><!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width" />
<title>偽SiReFaSo</title>
<link rel="stylesheet" href="./media/css/common.css" media="screen and (min-width: 481px)" />
<link rel="stylesheet" href="./media/css/smartphone.css" media="only screen and (max-width: 480px)" />
<link rel="help" href="./about.html" />
<link rel="alternate" type="application/rss+xml" href="./rss2.xml" />
</head>
<body>
	<header id="header">
		<div id="title-area">
			<h1 id="title"><a href="./">偽SiReFaSo</a></h1>
			<h2 id="subtitle">UKAGAKA Ghost Update Feed Generator</h2>
		</div>
		<section id="menu-area">
			<h2>navigation</h2>
			<nav class="category">
				<h3>categories</h3>
				<ul>
					<li class="about"><a href="./about.html">about</a></li>
				</ul>
			</nav>
		</section>
	</header>
	<section id="content" class="hfeed">
		<h2 class="entries-caption">entries</h2>
<?php for ($i = 0; $i < count($repos); $i++) { ?>
		<article id="<?php echo s($repos[$i]['id']); ?>" class="hentry autopagerize_page_element <?php echo s($repos[$i]['category']); ?> <?php echo s($repos[$i]['classname']); ?>">
			<h3 class="entry-title"><a href="<?php echo s($repos[$i]['html_url']); ?>" rel="bookmark"><?php echo s($repos[$i]['title']); ?></a></h3>
			<dl>
				<dt class="created">登録日時</dt>
				<dd class="created"><time datetime="<?php echo s($repos[$i]['created_at_time']); ?>"><?php echo s($repos[$i]['created_at_str']); ?></time></dd>
				<dt class="updated">最終更新</dt>
				<dd class="updated"><time datetime="<?php echo s($repos[$i]['updated_at_time']); ?>"><?php echo s($repos[$i]['updated_at_str']); ?></time></dd>
				<dt class="author">作者</dt>
				<dd class="author"><?php echo s($repos[$i]['author']); ?></dd>
			</dl>
		</article>
<?php } ?>
	</section>
	<footer id="footer">
		<p id="copyright"><small>Copyright &#169; 2022 <a href="./">偽SiReFaSo</a></small>, Generated by <a href="https://github.com/nikolat/github-dau-crawler">github-dau-crawler</a></p>
	</footer>
</body>
</html>
