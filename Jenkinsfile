pipeline {
    agent {
        kubernetes {
            yaml '''
                apiVersion: v1
                kind: Pod
                spec:
                  serviceAccountName: jenkins-admin
                  imagePullSecrets:
                  - name: dockerhub-credentials
                  containers:
                  - name: python
                    image: python:3.12
                    command: ["cat"]
                    tty: true
                    volumeMounts:
                    - mountPath: /home/jenkins/agent
                      name: workspace-volume
                    workingDir: /home/jenkins/agent
                  - name: docker
                    image: docker:23-dind
                    securityContext:
                      privileged: true
                    env:
                    - name: DOCKER_HOST
                      value: tcp://localhost:2375
                    - name: DOCKER_TLS_CERTDIR
                      value: ""
                    - name: DOCKER_BUILDKIT
                      value: "1"
                    volumeMounts:
                    - mountPath: /home/jenkins/agent
                      name: workspace-volume
                  - name: kubectl
                    image: bitnami/kubectl:1.30.7
                    command: ["/bin/sh"]
                    args: ["-c", "while true; do sleep 30; done"]
                    alwaysPull: true
                    securityContext:
                      runAsUser: 0
                    volumeMounts:
                    - mountPath: /home/jenkins/agent
                      name: workspace-volume
                  volumes:
                  - name: workspace-volume
                    emptyDir: {}
            '''
            defaultContainer 'python'
            inheritFrom 'default'
        }
    }
    options {
        timestamps()
        disableConcurrentBuilds()
    }
    environment {
        DOCKER_IMAGE = 'papakao/maya-sawa-v2'
        DOCKER_TAG = "${BUILD_NUMBER}"
    }
    stages {
        stage('Verify Repo') {
            steps {
                container('python') {
                    sh '''
                        set -e
                        ls -la
                        test -f pyproject.toml || { echo "pyproject.toml not found"; exit 1; }
                    '''
                }
            }
        }

        stage('Install Dependencies') {
            steps {
                container('python') {
                    sh '''
                        set -e
                        pip install --no-cache-dir poetry
                        poetry config virtualenvs.create false
                        poetry install --no-root --only main
                    '''
                }
            }
        }

        stage('Build & Push Image') {
            steps {
                container('docker') {
                    withCredentials([usernamePassword(credentialsId: 'dockerhub-credentials', usernameVariable: 'DOCKER_USERNAME', passwordVariable: 'DOCKER_PASSWORD')]) {
                        sh '''
                            set -e
                            cd "${WORKSPACE}"
                            test -f Dockerfile || { echo "Dockerfile not found"; exit 1; }
                            echo "${DOCKER_PASSWORD}" | docker login -u "${DOCKER_USERNAME}" --password-stdin
                            docker build \
                              --build-arg BUILDKIT_INLINE_CACHE=1 \
                              --cache-from ${DOCKER_IMAGE}:latest \
                              -t ${DOCKER_IMAGE}:${DOCKER_TAG} \
                              -t ${DOCKER_IMAGE}:latest \
                              .
                            docker push ${DOCKER_IMAGE}:${DOCKER_TAG}
                            docker push ${DOCKER_IMAGE}:latest
                        '''
                    }
                }
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                container('kubectl') {
                    withCredentials([
                        string(credentialsId: 'OPENAI_API_KEY', variable: 'OPENAI_API_KEY'),
                        string(credentialsId: 'OPENAI_ORGANIZATION', variable: 'OPENAI_ORGANIZATION'),
                        string(credentialsId: 'MAYA_V2_SECRET_KEY', variable: 'MAYA_V2_SECRET_KEY'),
                        string(credentialsId: 'DB_HOST', variable: 'DB_HOST'),
                        string(credentialsId: 'DB_PORT', variable: 'DB_PORT'),
                        string(credentialsId: 'DB_DATABASE', variable: 'DB_DATABASE'),
                        string(credentialsId: 'DB_USERNAME', variable: 'DB_USERNAME'),
                        string(credentialsId: 'DB_PASSWORD', variable: 'DB_PASSWORD'),
                        string(credentialsId: 'REDIS_HOST', variable: 'REDIS_HOST'),
                        string(credentialsId: 'REDIS_CUSTOM_PORT', variable: 'REDIS_CUSTOM_PORT'),
                        string(credentialsId: 'REDIS_PASSWORD', variable: 'REDIS_PASSWORD'),
                        string(credentialsId: 'REDIS_QUEUE_MAYA', variable: 'REDIS_QUEUE_MAYA'),
                        string(credentialsId: 'PUBLIC_API_BASE_URL', variable: 'PUBLIC_API_BASE_URL')
                    ]) {
                        withCredentials([usernamePassword(credentialsId: 'dockerhub-credentials', usernameVariable: 'DOCKER_USERNAME', passwordVariable: 'DOCKER_PASSWORD')]) {
                            sh '''
                                set -e

                                kubectl cluster-info

                                # Ensure Docker Hub imagePullSecret exists in default namespace
                                kubectl create secret docker-registry dockerhub-credentials \
                                  --docker-server=https://index.docker.io/v1/ \
                                  --docker-username="${DOCKER_USERNAME}" \
                                  --docker-password="${DOCKER_PASSWORD}" \
                                  --docker-email="none" \
                                  -n default \
                                  --dry-run=client -o yaml | kubectl apply -f -

                                test -f k8s/deployment.yaml || { echo "k8s/deployment.yaml missing"; exit 1; }
                                test -f k8s/cronjob.yaml || echo "k8s/cronjob.yaml not found, skipping cronjobs"

                                echo "Applying manifests ..."
                                # Export variables used by the templates
                                export DATABASE_URL="postgres://${DB_USERNAME}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_DATABASE}?sslmode=require"
                                export REDIS_URL="redis://:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_CUSTOM_PORT}/0"
                                export CELERY_BROKER_URL="$REDIS_URL"
                                export CELERY_RESULT_BACKEND="$REDIS_URL"
                                export REDIS_QUEUE_MAYA_V2="${REDIS_QUEUE_MAYA:-maya_v2}"

                                # Apply Deployment/Service/Worker
                                kubectl apply -f k8s/deployment.yaml

                                # Optionally apply CronJob if present
                                if [ -f k8s/cronjob.yaml ]; then
                                  kubectl apply -f k8s/cronjob.yaml
                                fi

                                # Rollout status
                                kubectl rollout status deployment/maya-sawa-v2 -n default
                            '''
                        }
                    }
                }
            }
        }
    }
    post {
        always {
            script {
                if (env.WORKSPACE) {
                    cleanWs()
                }
            }
        }
    }
}


