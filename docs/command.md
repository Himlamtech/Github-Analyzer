# Demo Commands

## Muc tieu

Tai lieu nay chua cac lenh de demo dashboard `Demo SaaS` theo dung flow:

1. He thong nhin ben ngoai van on
2. Request van vao binh thuong
3. Tat `processor` de tao su co silent failure
4. Dashboard chi ra van de o tang xu ly noi bo
5. Trace va logs xac nhan root cause

Tat ca lenh ben duoi deu tranh dung `rg` de chay duoc tren may chi co `grep`.

## 1. Mo cac man hinh can thiet

Mo 3 tab truoc khi demo:

- Grafana: `http://localhost:3001/d/demo-saas/demo-saas`
- API Docs: `http://localhost:8000/docs`
- Terminal

## 2. Kiem tra stack dang chay

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E 'gha-(api|poller|processor|grafana|prometheus|clickhouse|kafka|tempo)'
```

Ky vong:

- `gha-api`
- `gha-poller`
- `gha-processor`
- `gha-grafana`
- `gha-prometheus`
- `gha-clickhouse`
- `gha-kafka`
- `gha-tempo`

## 3. Tao traffic nhe truoc khi demo

Lenh nay giup `Requests / s` va `Latency` co so lieu ngay tu dau:

```bash
for i in $(seq 1 30); do curl -s http://localhost:8000/health >/dev/null; sleep 0.2; done
```

Neu muon tao them trace business:

```bash
for i in $(seq 1 5); do curl -s http://localhost:8000/pipeline/status >/dev/null; sleep 1; done
```

## 3.1. Dau hieu ky vong khi su co xay ra

Day la nhung dau hieu can quan sat sau khi tat `processor`:

- `Throughput` o nhanh xu ly se giam rat manh, co the ve gan `0`
- `Kafka Lag` hoac do lech giua produced va processed se tang dan
- `Data Freshness` se tang lien tuc vi khong con ban ghi moi duoc xu ly
- `Latest Ingest Timestamp` co xu huong dung lai
- `API Health`, `Request Rate`, `Error Rate`, va ca `Latency` co the van khong bao dong ro rang

Thong diep can giu nhat quan:

- day la su co o tang xu ly bat dong bo, khong nhat thiet la su co lam request API cham hon ro ret
- trace va logs duoc dung de correlate mot request thanh cong voi tinh trang pipeline bi stale
- root cause duoc xac nhan bang business telemetry va processor logs, khong phai bang mot span request bi block boi processor

## 4. Kich ban demo binh thuong

Noi khi dang mo dashboard:

- `API Health` van xanh
- `Pod Running` van du
- `Error Rate` thap
- `Request Rate` da co traffic

Tao them request truoc mat nguoi xem:

```bash
for i in $(seq 1 20); do curl -s http://localhost:8000/health >/dev/null; done
for i in $(seq 1 5); do curl -s http://localhost:8000/pipeline/status >/dev/null; sleep 1; done
```

## 5. Lay trace id de drilldown

Lenh nay tra ve response header. Tim header `X-Trace-Id`:

```bash
curl -i -s http://localhost:8000/pipeline/status
```

Dung header do de noi:

- request van thanh cong
- trace giup correlate sang logs va metrics

## 6. Tao su co silent failure

Tat processor Spark:

```bash
docker stop gha-processor
```

Noi luc nay:

- toi chi tat processor
- toi khong tat API
- user van goi request duoc

Tiep tuc tao request de chung minh lop API van song:

```bash
for i in $(seq 1 15); do curl -s http://localhost:8000/health >/dev/null; sleep 0.5; done
for i in $(seq 1 5); do curl -s http://localhost:8000/pipeline/status >/dev/null; sleep 1; done
```

Cho `20-40s` de Grafana refresh.

## 7. Thu tu doc dashboard

### Hang 1: Nhin Ngoai Van On

Noi:

- API van `Up`
- request van vao
- error rate khong nhat thiet tang

### Hang 2: Nhung Business Dang Sai

Noi:

- `Throughput` bat dau lech
- `Kafka Lag` tang
- `Data Ingest Freshness` xau di
- `Latest Ingest Timestamp` dung lai

Thong diep:

- monitoring truyen thong cho thay he thong con song
- nhung business value da ngung chay

### Hang 3: Dau Hieu O Lop Request

Noi:

- latency khong nhat thiet no
- top slow endpoints khong chi ra root cause

Thong diep:

- request-level monitoring chua du

### Hang 4: Dieu Tra Root Cause

Noi:

- lay mot request thanh cong
- mo trace correlation
- doi chieu logs va metrics
- nhan manh trace nay dung de correlate, khong phai de chung minh request dang doi processor

### Hang 5: Xac Nhan Cuoi

Noi:

- processor logs dung hoac mat log moi
- timeline xac nhan processor la diem gay

## 8. Khoi phuc sau demo

Bat lai processor:

```bash
docker start gha-processor
```

Theo doi logs:

```bash
docker logs -f gha-processor
```

Neu poller dung bat thuong thi restart:

```bash
docker restart gha-poller
```

## 9. Kiem tra nhanh sau khi khoi phuc

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E 'gha-(api|poller|processor|grafana|prometheus|clickhouse|kafka|tempo)'
```

```bash
for i in $(seq 1 10); do curl -s http://localhost:8000/health >/dev/null; done
for i in $(seq 1 5); do curl -s http://localhost:8000/pipeline/status >/dev/null; sleep 1; done
```

## 10. Script noi 60 giay

Ban co the noi gan nhu nguyen van:

```text
Nhin hang dau tien, neu chi dung monitoring truyen thong thi he thong dang on.
API van up, request van vao, error rate van thap.

Bay gio toi tat processor, nhung toi khong tat API.
Nghia la ben ngoai he thong van con song.

Chi sau vai chuc giay, nhin sang hang business:
throughput lech, Kafka lag tang, freshness xau di, va latest ingest timestamp dung lai.

Latency va error rate khong nhat thiet bao dong.
Nghia la request-layer monitoring khong du de ket luan root cause.

Luc nay trace va logs moi chi ra duoc su that:
API van thanh cong, nhung processor da ngung xu ly.
Trace giup noi request thanh cong voi tinh trang pipeline stale,
con logs processor va metrics business moi xac nhan diem gay.

Do la khac biet giua monitoring va observability:
monitoring cho biet service con song,
con observability cho biet business outcome con dung hay khong.
```
