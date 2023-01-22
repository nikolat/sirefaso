import crawler
import datetime
import zoneinfo

class GitHubDauCrawler(crawler.GitHubApiCrawler):

	__DENIED_CATEGORIES = ['media', 'author']

	def __init__(self):
		super().__init__('nikolat/GitHubDauCrawler')

	def crawl(self):
		jst = zoneinfo.ZoneInfo('Asia/Tokyo')
		now = datetime.datetime.now(jst)
		logger = self._logger
		config = self._config
		responses = self._responses
		entries = []
		categories = []
		authors = []
		for response in responses:
			for item in response.json()['items']:
				types = [t.replace('ukagaka-', '') for t in item['topics'] if 'ukagaka-' in t]
				if len(types) == 0:
					logger.debug(f'ukagaka-* topic is not found in {item["full_name"]}')
					continue
				types = [t for t in types if t not in self.__DENIED_CATEGORIES]
				if len(types) == 0:
					logger.debug(f'ukagaka-* topic is not allowed in {item["full_name"]}')
					continue
				category = types[0]
				if item['full_name'] in config['redirect']:
					logger.debug(f'redirected form {item["full_name"]} to {config["redirect"][item["full_name"]]}')
					url = 'https://api.github.com/repos/' + config['redirect'][item['full_name']]
					r = self._request_with_retry(url, None, logger)
					r_item = r.json()
					item['created_at'] = r_item['created_at']
					item['pushed_at'] = r_item['pushed_at']
				dt_created = datetime.datetime.strptime(item['created_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc).astimezone(tz=jst)
				dt_updated = datetime.datetime.strptime(item['pushed_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc).astimezone(tz=jst)
				diff = now - dt_updated
				if diff.days < 1:
					classname = 'days-over-0'
				elif diff.days < 7:
					classname = 'days-over-1'
				elif diff.days < 30:
					classname = 'days-over-7'
				elif diff.days < 365:
					classname = 'days-over-30'
				else:
					classname = 'days-over-365'
				entry = {
					'id': item['full_name'],
					'title': item['name'],
					'category': category,
					'classname': classname,
					'author': item['owner']['login'],
					'author_url': item['owner']['html_url'],
					'author_avatar': item['owner']['avatar_url'],
					'content_text': '',
					'summary': item['description'] if item['description'] is not None else '',
					'tags': item['topics'],
					'html_url': item['html_url'],
					'created_at_time': item['created_at'],
					'created_at_str': dt_created.strftime('%Y-%m-%d %H:%M:%S'),
					'updated_at_time': item['pushed_at'],
					'updated_at_str': dt_updated.strftime('%Y-%m-%d %H:%M:%S'),
					'updated_at_rss2': dt_updated.strftime('%a, %d %b %Y %H:%M:%S %z')
				}
				entries.append(entry)
				if category not in categories:
					categories.append(category)
				if item['owner']['login'] not in authors:
					authors.append(item['owner']['login'])
		self._entries = entries
		self._categories = categories
		self._authors = authors
		return self

	def _get_feed_dict(self, title, base_url, description, entries):
		return {
			'version': 'https://jsonfeed.org/version/1.1',
			'title': title,
			'home_page_url': base_url,
			'feed_url': f'{base_url}{self._JSON_FEED_FILENAME}',
			'description': description,
			'items': [
				{
					'id': e['id'],
					'url': e['html_url'],
					'title': e['title'],
					'content_text': e['content_text'],
					'summary': e['summary'],
					'date_published': e['created_at_time'],
					'date_modified': e['updated_at_time'],
					'authors': [
						{
							'name': e['author'],
							'url': e['author_url'],
							'avatar': e['author_avatar']
						}
					],
					'tags': e['tags']
				}
			for e in entries]
		}

if __name__ == '__main__':
	g = GitHubDauCrawler()
	g.search().crawl().export()
