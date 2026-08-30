pipeline {
  agent any
  options {
    timestamps()
    disableConcurrentBuilds()
  }
  environment {
    IMAGE = "ghcr.io/ananyanagaraj11/aetherforge:${env.BUILD_NUMBER}"
    KUBE_NS = "aetherforge"
  }
  stages {
    stage('Lint') {
      steps {
        sh 'python -m pip install ruff==0.8.3'
        sh 'ruff check src tests'
      }
    }
    stage('Test') {
      steps {
        sh 'python -m pip install -r requirements.txt'
        sh 'python -m pytest tests -q'
      }
    }
    stage('Image') {
      when { branch 'main' }
      steps {
        sh 'docker build -t $IMAGE .'
      }
    }
    stage('Deploy staging') {
      when { branch 'main' }
      steps {
        sh 'kubectl apply -f infra/kubernetes -n $KUBE_NS'
        sh 'kubectl -n $KUBE_NS set image deploy/aetherforge-api api=$IMAGE'
        sh 'kubectl -n $KUBE_NS rollout status deploy/aetherforge-api'
      }
    }
    stage('Promote production') {
      when { branch 'main' }
      steps {
        input message: 'HITL + Jira CAB Approved required before production', ok: 'Promote'
        sh 'kubectl -n $KUBE_NS set image deploy/aetherforge-api api=$IMAGE'
      }
    }
  }
  post {
    always {
      echo 'Write build status back to the linked AF Jira issue'
    }
  }
}
