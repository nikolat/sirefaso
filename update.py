import re
import datetime
import zoneinfo
import requests
import yaml
from jinja2 import Environment, FileSystemLoader

if __name__ == '__main__':
	jst = zoneinfo.ZoneInfo('Asia/Tokyo')
	config_filename = 'config.yml'
	with open(config_filename, encoding='utf-8') as file:
		config = yaml.safe_load(file)
	url = 'https://api.github.com/search/repositories'
	payload = {'q': f'topic:{config["search_key"]}', 'sort': 'updated'}
	responses = []
	response = requests.get(url, params=payload)
	response.raise_for_status()
	responses.append(response)
	pattern = re.compile(r'<(.+?)>; rel="next"')
	result = pattern.search(response.headers['link']) if 'link' in response.headers else None
	while result:
		url = result.group(1)
		response = requests.get(url)
		response.raise_for_status()
		responses.append(response)
		result = pattern.search(response.headers['link']) if 'link' in response.headers else None
	now = datetime.datetime.now(jst)
	entries = []
	for response in responses:
		for item in response.json()['items']:
			types = [t.replace('ukagaka-', '') for t in item['topics'] if 'ukagaka-' in t]
			if len(types) == 0:
				continue
			if item['full_name'] in config['redirect']:
				url = 'https://api.github.com/repos/' + config['redirect'][item['full_name']]
				r = requests.get(url)
				r.raise_for_status()
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
				'category': types[0],
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
	env = Environment(loader=FileSystemLoader('./templates', encoding='utf8'), autoescape=True)
	data = {
		'entries': entries,
		'config': config
	}
	for filename in ['index.html', 'rss2.xml']:
		template = env.get_template(filename)
		rendered = template.render(data)
		with open(f'docs/{filename}', 'w', encoding='utf-8') as f:
			f.write(rendered + '\n')
