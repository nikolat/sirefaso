<?php
date_default_timezone_set('Asia/Tokyo');
if (!file_exists('./docs/')) {
    mkdir('./docs');
}
$max = 30;
$next_filename = 'repos0.txt';
$lines = file(__DIR__. '/repos/'. $next_filename, FILE_IGNORE_NEW_LINES);
$header_end = false;
$json = '';
foreach ($lines as $line) {
    if ($header_end) {
        $json = $line;
        break;
    }
    elseif ($line === '') {
        $header_end = true;
    }
}
if ($json === '') {
    throw new \RuntimeException('file not found.');
}
$data_repos = json_decode($json, true);
$n = $data_repos['total_count'];
if ($n > $max) {
    $n = $max;
}
$repos = [];
$c = 0;
$date_now = strtotime('now');
for ($i = 0; $i < $n; $i++) {
    $item = $data_repos['items'][$i];
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
    $repo = [
        'title' => $item['name'],
        'link' => $item['html_url'],
        'pubdate' => date('D, d M Y H:i:s O', strtotime($item['pushed_at']))
    ];
    $repos[$c] = $repo;
    $c++;
}

$myurl = 'https://nikolat.github.io/sirefaso/';
$mypath = dirname(__FILE__);
$myname = mb_encode_numericentity('偽SiReFaSo', array( 0x0, 0x10ffff, 0, 0xffffff ), 'UTF-8');
$mydescription = mb_encode_numericentity('GitHubで公開されている伺か関連アプリの更新情報を一覧表示する', array( 0x0, 0x10ffff, 0, 0xffffff ), 'UTF-8');

$fp = fopen($mypath. '/docs/rss2.xml', 'w');
fwrite($fp, '<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
<title>'. $myname. '</title>
<link>'. $myurl. '</link>
<description>'. $mydescription. '</description>
<atom:link href="'. $myurl. 'rss2.xml" rel="self" type="application/rss+xml" />
');

foreach($repos as $r) {
    fwrite($fp, '<item>
    <title>'. $r['title']. '</title>
    <link>'. $r['link']. '</link>
    <guid>'. $r['link']. '</guid>
    <pubDate>'. $r['pubdate']. '</pubDate>
</item>'. "\n");
}

fwrite($fp, '</channel>
</rss>
');
fclose($fp);
