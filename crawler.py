import re
import datetime
import logging
import shutil
import os
import time
import requests
import yaml
import abc
import json
from jinja2 import Environment, FileSystemLoader

class GitHubApiCrawler(abc.ABC):

	__CONFIG_FILENAME = 'config.yml'
	__JSON_FEED_FILENAME = 'feed.json'

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
				logger.debug(f'Sleeping to retry after {wait} seconds.')
				time.sleep(wait)
				response = requests.get(url, params=payload, headers=headers)
				try:
					response.raise_for_status()
				except requests.RequestException as e:
					logger.warning(f'Status: {response.status_code}, URL: {url}')
					logger.debug(e.response.text)
					raise
				else:
					logger.debug(f'Status: {response.status_code}, URL: {url}')
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

	def __get_feed_dict(self, title, base_url, entries):
		return {
			'version': 'https://jsonfeed.org/version/1.1',
			'title': title,
			'home_page_url': base_url,
			'feed_url': f'{base_url}{self.__JSON_FEED_FILENAME}',
			'description': self._config['site_description'],
			'items': [{'id': e['id'], 'url': e['html_url'], 'title': e['title'], 'date_published': e['created_at_time'], 'date_modified': e['updated_at_time']} for e in entries]
		}

	def export(self):
		config = self._config
		entries = self._entries
		categories = self._categories
		authors = self._authors
		filename_json = self.__JSON_FEED_FILENAME
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
		with open(f'docs/{filename_json}', 'w', encoding='utf-8') as f:
			json.dump(self.__get_feed_dict(config['site_title'], config['self_url'], entries), f, ensure_ascii=False, indent=4)
		# category
		for category in categories:
			shutil.rmtree(f'docs/{category}/', ignore_errors=True)
			os.mkdir(f'docs/{category}/')
			target_entries = [e for e in entries if e['category'] == category]
			data = {
				'entries': target_entries,
				'config': config
			}
			for filename in ['index.html', 'rss2.xml']:
				template = env.get_template(f'category/{filename}')
				rendered = template.render(data)
				with open(f'docs/{category}/{filename}', 'w', encoding='utf-8') as f:
					f.write(rendered + '\n')
			with open(f'docs/{category}/{filename_json}', 'w', encoding='utf-8') as f:
				json.dump(self.__get_feed_dict(f'{category} | {config["site_title"]}', f'{config["self_url"]}{category}/', target_entries), f, ensure_ascii=False, indent=4)
		# author
		shutil.rmtree('docs/author/', ignore_errors=True)
		os.mkdir('docs/author/')
		for author in authors:
			os.mkdir(f'docs/author/{author}/')
			target_entries = [e for e in entries if e['author'] == author]
			data = {
				'entries': target_entries,
				'config': config
			}
			for filename in ['index.html', 'rss2.xml']:
				template = env.get_template(f'author/{filename}')
				rendered = template.render(data)
				with open(f'docs/author/{author}/{filename}', 'w', encoding='utf-8') as f:
					f.write(rendered + '\n')
			with open(f'docs/author/{author}/{filename_json}', 'w', encoding='utf-8') as f:
				json.dump(self.__get_feed_dict(f'{author} | {config["site_title"]}', f'{config["self_url"]}author/{author}/', target_entries), f, ensure_ascii=False, indent=4)
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
