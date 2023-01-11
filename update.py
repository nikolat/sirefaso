import re
import datetime
import logging
import shutil
import os
import time
import zoneinfo
import requests
import yaml
import abc
from jinja2 import Environment, FileSystemLoader

class GitHubApiCrawler(abc.ABC):

	__CONFIG_FILENAME = 'config.yml'

	def __init__(self, user_agent='nikolat/GitHubApiCrawler'):
		self._logger = self.__get_custom_logger()
		with open(self.__CONFIG_FILENAME, encoding='utf-8') as file:
			self._config = yaml.safe_load(file)
		self.__user_agent = user_agent

	def __get_custom_logger(self):
		custom_logger = logging.getLogger('custom_logger')
		custom_logger.setLevel(logging.DEBUG)
		handler = logging.StreamHandler()
		handler.setLevel(logging.DEBUG)
		custom_logger.addHandler(handler)
		handler_formatter = logging.Formatter(
			'%(asctime)s - [%(levelname)s]: %(message)s', datefmt='%Y-%m-%dT%H:%M:%SZ'
		)
		handler_formatter.converter = time.gmtime
		handler.setFormatter(handler_formatter)
		return custom_logger

	def _request_with_retry(self, url, payload, retry=True):
		logger = self._logger
		headers = {
			'Accept': 'application/vnd.github+json',
			'Authorization': f'Bearer {os.getenv("GITHUB_TOKEN")}',
			'X-GitHub-Api-Version': '2022-11-28',
			'User-Agent': self.__user_agent
		}
		response = requests.get(url, params=payload, headers=headers)
		try:
			response.raise_for_status()
		except requests.RequestException as e:
			logger.warning(f'Status: {response.status_code}, URL: {url}')
			logger.debug(e.response.text)
			if retry:
				if 'Retry-After' in response.headers:
					wait = int(response.headers['Retry-After'])
				else:
					wait = 180
				logger.debug(f'wait = {wait}')
				time.sleep(wait)
				response = requests.get(url, params=payload, headers=headers)
				logger.debug(f'Status: {response.status_code}')
				try:
					response.raise_for_status()
				except requests.RequestException as e:
					logger.warning(f'Status: {response.status_code}, URL: {url}')
					logger.debug(e.response.text)
					raise
		return response

	def search(self):
		config = self._config
		url = 'https://api.github.com/search/repositories'
		payload = {'q': config['search_query'], 'sort': 'updated'}
		responses = []
		response = self._request_with_retry(url, payload)
		responses.append(response)
		pattern = re.compile(r'<(.+?)>; rel="next"')
		result = pattern.search(response.headers['link']) if 'link' in response.headers else None
		while result:
			url = result.group(1)
			response = self._request_with_retry(url, None)
			responses.append(response)
			result = pattern.search(response.headers['link']) if 'link' in response.headers else None
		self._responses = responses
		return self

	@abc.abstractmethod
	def crawl(self):
		self._entries = []
		self._categories = []
		self._authors = []
		return self

	def export(self):
		config = self._config
		entries = self._entries
		categories = self._categories
		authors = self._authors
		env = Environment(loader=FileSystemLoader('./templates', encoding='utf8'), autoescape=True)
		# top page
		data = {
			'entries': entries,
			'config': config
		}
		for filename in ['index.html', 'rss2.xml']:
			template = env.get_template(filename)
			rendered = template.render(data)
			with open(f'docs/{filename}', 'w', encoding='utf-8') as f:
				f.write(rendered + '\n')
		# category
		for category in categories:
			shutil.rmtree(f'docs/{category}/', ignore_errors=True)
			os.mkdir(f'docs/{category}/')
			data = {
				'entries': [e for e in entries if e['category'] == category],
				'config': config
			}
			for filename in ['index.html', 'rss2.xml']:
				template = env.get_template(f'category/{filename}')
				rendered = template.render(data)
				with open(f'docs/{category}/{filename}', 'w', encoding='utf-8') as f:
					f.write(rendered + '\n')
		# author
		shutil.rmtree('docs/author/', ignore_errors=True)
		os.mkdir('docs/author/')
		for author in authors:
			os.mkdir(f'docs/author/{author}/')
			data = {
				'entries': [e for e in entries if e['author'] == author],
				'config': config
			}
			for filename in ['index.html', 'rss2.xml']:
				template = env.get_template(f'author/{filename}')
				rendered = template.render(data)
				with open(f'docs/author/{author}/{filename}', 'w', encoding='utf-8') as f:
					f.write(rendered + '\n')
		# sitemap
		data = {
			'categories': categories,
			'authors': authors,
			'now': datetime.datetime.now().strftime('%Y-%m-%d'),
			'config': config
		}
		filename = 'sitemap.xml'
		template = env.get_template(filename)
		rendered = template.render(data)
		with open(f'docs/{filename}', 'w', encoding='utf-8') as f:
			f.write(rendered + '\n')
		return self

class GitHubDauCrawler(GitHubApiCrawler):

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
					'id': item['full_name'].replace('/', '_'),
					'title': item['name'],
					'category': category,
					'classname': classname,
					'author': item['owner']['login'],
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

if __name__ == '__main__':
	g = GitHubDauCrawler()
	g.search().crawl().export()
