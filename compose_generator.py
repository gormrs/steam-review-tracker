import json
import yaml


def generate_docker_compose():
    with open('src/settings.json') as f:
        data = json.load(f)

    services = {}
    for app_id in data['apps']:
        if data['apps'][app_id]['track']:
            services['steamworker_{}'.format(app_id)] = {
                'build': '.',
                'environment': [
                    'APP_ID={}'.format(app_id),
                ]
            }

    docker_compose = {
        'version': '3',
        'services': services
    }

    with open('docker-compose.yml', 'w') as f:
        yaml.dump(docker_compose, f, default_flow_style=False)

if __name__ == '__main__':
    generate_docker_compose()
