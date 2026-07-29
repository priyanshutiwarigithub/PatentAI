# SSH Deployment Checklist — PatentMind AI

Target GPU Server: `192.168.6.50` (SSH Port `22`, User `gpuuser`)

## 1. AWS Infrastructure Deployment (Terraform)
```bash
cd patentmind/terraform
terraform init
terraform plan
terraform apply -auto-approve
```

## 2. Remote GPU Server Setup (192.168.6.50)
### Step A: Start Qdrant Vector DB
```bash
ssh -p 22 gpuuser@192.168.6.50
./qdrant --config-path qdrant_config.yaml &
```

### Step B: Start Ollama & Pull Qwen3-4B
```bash
ollama serve &
ollama pull qwen3:4b
```

## 3. Data Processing Batch Jobs (GPU)
### Step C: Run Patent Data Ingestion
```bash
python -m patentmind.ingestion.pipeline
```

### Step D: Run Document Processing Pipeline (GLM-OCR GPU)
```bash
python -m patentmind.processing.pipeline
```

### Step E: Run GPU Embedding Generation & Vector Storage
```bash
python -m patentmind.embeddings.pipeline
```

## 4. Launch FastAPI + React Web Stack
```bash
uvicorn patentmind.api.main:app --host 0.0.0.0 --port 8000
```

## 5. Local Tunneling for Web Demo
```bash
ssh -N -L 8000:localhost:8000 gpuuser@192.168.6.50 -p 22
```
Access the application at `http://localhost:8000`.
