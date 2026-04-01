# Dashboard Product Wireframe

## Overview

Tai lieu nay de xac dinh lai dashboard theo goc nhin product cho du an thong ke GitHub AI:

- Du lieu va tang luu tru da tot o muc POC.
- Van de hien tai nam o cach su dung du lieu va bieu dien du lieu.
- Muc tieu moi khong phai chi "co so lieu", ma phai "show off duoc insight" de nguoi dung nhin vao la thay ngay top movers, top categories, top language, va xu huong tang truong.

Pham vi tai lieu:

- wireframe layout
- de xuat loai chart cho tung use case
- current state va gap ky thuat
- backlog implementation theo huong frontend + API

Khong nam trong pham vi tai lieu nay:

- SQL chi tiet
- pixel-perfect visual design
- implementation code

## Current State

### Da co trong frontend

Trang dashboard hien tai o [frontend/app/page.tsx](/home/iec/lamnh/github/frontend/app/page.tsx) dang co cac khoi:

- bo loc category va days
- category summary grid
- `Top Repositories` dang hien thi dang table
- `Trending Repos`
- `Star Growth Chart`
- `Topic Heatmap`
- `Language Distribution`
- `Activity Timeline`

Component hien tai cho bang repo nam o [frontend/components/dashboard/TopReposTable.tsx](/home/iec/lamnh/github/frontend/components/dashboard/TopReposTable.tsx).

### Da co trong frontend API layer

[frontend/lib/api.ts](/home/iec/lamnh/github/frontend/lib/api.ts) dang cho thay frontend ky vong co cac endpoint:

- `/dashboard/top-repos`
- `/dashboard/trending`
- `/dashboard/topic-breakdown`
- `/dashboard/language-breakdown`
- `/dashboard/repo-timeseries`
- `/dashboard/category-summary`

### Search state

Search UI dang nam o [frontend/components/ai/AISearchPanel.tsx](/home/iec/lamnh/github/frontend/components/ai/AISearchPanel.tsx).

Nhung hien tai co mot blocker ro rang:

- `AISearchPanel.tsx` import `@/hooks/useAISearch`
- file hook nay khong ton tai trong `frontend/hooks/`

Dieu nay co nghia la tinh nang search hien tai chua o trang thai product-ready, va co kha nang dang broken o build/runtime path.

### Backend/API state

Source backend hien tai co route AI o [src/presentation/api/ai_routes.py](/home/iec/lamnh/github/src/presentation/api/ai_routes.py).

Test suite lai cho thay he thong tung ky vong co dashboard routes o [tests/presentation/test_dashboard_routes.py](/home/iec/lamnh/github/tests/presentation/test_dashboard_routes.py), nhung source file `src/presentation/api/dashboard_routes.py` hien khong co trong worktree.

## Gap

### Gap 1: Top Repositories chua dung use case product

Khoi `Top Repositories` hien tai dang bi thien ve "bang du lieu" hon la "bang insight":

- kho scan nhanh
- kho thay repo nao dang rise manh
- chua tach ro "top by size" va "top by momentum"
- chua tao duoc cam giac noi bat cho top 20

### Gap 2: Cac top list chua du day

Use case mong muon can it nhat 4 nhom top:

- Top 20 Repositories
- Top 20 Language
- Top 20 Raise Repositories in Week
- Top 20 Categories

Hien tai UI da co mot vai khoi lien quan, nhung chua duoc to chuc thanh mot storytelling dashboard ro rang.

### Gap 3: Search chua hoat dong on dinh

Search hien khong nen duoc xem la usable cho end user vi:

- thieu hook frontend
- chua ro integration entry point tren page
- chua co fallback UX ro rang cho truong hop semantic service khong san sang

### Gap 4: Chua co hierarchy product

Dashboard hien tai co nhieu widget, nhung chua sap xep theo cap do quan trong:

1. hard numbers
2. market movers
3. structural breakdown
4. exploration/search
5. drilldown

## Target State

Dashboard moi can tra loi nhanh 5 cau hoi:

1. Thi truong AI GitHub tuan nay dang tang o dau?
2. Repo nao dang dan dau theo quy mo?
3. Repo nao dang tang nhanh nhat trong tuan?
4. Language va category nao dang chiem uu the?
5. Toi co the search theo use case va drill down vao repo nao?

Nguyen tac trinh bay:

- hard numbers compact va scan nhanh trong 3-5 giay
- top lists phai noi bat, khong an sau bang text dai
- bang chi dung cho so lieu can doi chieu chinh xac
- chart dung de show hierarchy, momentum, concentration, rotation
- search phai duoc dat nhu mot "discovery surface", khong phai mot form phu

## Recommended Information Architecture

### Section 1: Executive Snapshot

Hang dau tien chi de tra loi "what matters now":

- Total tracked repositories
- Total stars observed in selected window
- Total weekly star gain
- Active languages
- Active categories
- Search box global

Dang hien thi de xuat:

- 4 hoac 5 KPI cards nho, so lon, subtitle rat ngan
- 1 search input rong nam cung hang, hoac chiem 1 card lon hon

### Section 2: Market Leaders

Day la hang quan trong nhat cua dashboard moi.

Gom 2 khoi dat canh nhau:

- `Top 20 Repositories`
- `Top 20 Raise Repositories in Week`

Khong nen de ca 2 khoi deu la table.

De xuat:

- Khoi trai: ranked bar chart card cho `Top 20 Repositories`
- Khoi phai: lollipop chart hoac vertical momentum list cho `Top 20 Raise Repositories in Week`

Ly do:

- top repo can nhin thay hierarchy nhanh
- rise repo can nhin thay delta tuan nay, khong bi nham voi tong stars

### Section 3: Structure of the Market

Gom 2 khoi:

- `Top 20 Language`
- `Top 20 Categories`

De xuat:

- Language: horizontal bar chart hoac treemap
- Categories: packed bubble, donut + ranked list, hoac heat-strip

Neu can show dong thoi size va growth:

- dung scatter plot:
  - truc X: total stars
  - truc Y: weekly growth
  - bubble size: repo count

### Section 4: Rotation and Heat

Day la tang "storytelling", khong phai tang so lieu goc.

Gom:

- topic heatmap
- category rotation
- activity timeline

Khoi nay nen xuong hang sau, vi no phuc vu phan tich sau khi user da nhin thay top movers.

### Section 5: Search and Drilldown

Search khong nen la mot panel AI tach roi. No nen la mot tang kham pha.

De xuat:

- search box dat o hero hoac sticky tren cung
- ket qua search mo ra thanh result deck
- click vao repo se mo drilldown drawer/panel

Drilldown panel gom:

- star growth 7d / 30d
- category
- language
- topics
- why trending
- related repos

## Wireframe

### Desktop Wireframe

```text
+--------------------------------------------------------------------------------------+
| HEADER                                                                               |
| GitHub AI Market Pulse                                 [category] [7d/30d] [search] |
+--------------------------------------------------------------------------------------+
| KPI: Tracked Repos | KPI: Weekly Star Gain | KPI: Active Languages | KPI: Categories |
+--------------------------------------------------------------------------------------+
| TOP 20 REPOSITORIES                           | TOP 20 RAISE REPOSITORIES IN WEEK    |
| ranked horizontal bars                        | lollipop / momentum bars             |
| repo + total stars + category chip            | repo + weekly delta + growth badge   |
+--------------------------------------------------------------------------------------+
| TOP 20 LANGUAGE                               | TOP 20 CATEGORIES                    |
| treemap or bar ranking                        | bubble / donut + ranked side list    |
+--------------------------------------------------------------------------------------+
| TOPIC HEATMAP                                 | CATEGORY ROTATION / WEEK IN REVIEW   |
+--------------------------------------------------------------------------------------+
| SEARCH RESULTS / DISCOVERY DECK                                                       |
| cards with why matched, language, category, stars, weekly raise                      |
+--------------------------------------------------------------------------------------+
| REPOSITORY DRILLDOWN                                                                |
| star growth chart | activity timeline | why trending | related repos                 |
+--------------------------------------------------------------------------------------+
```

### Mobile Wireframe

```text
[Header]
[Filter Row]
[Search]
[KPI Carousel]
[Top 20 Repositories]
[Top 20 Raise Repositories in Week]
[Top 20 Language]
[Top 20 Categories]
[Topic Heatmap]
[Search Results]
[Repo Drilldown]
```

## Visual Recommendation By Metric

| Metric block | Primary visual | Secondary visual | Why |
|---|---|---|---|
| Top 20 Repositories | Horizontal ranked bar chart | Compact table toggle | Dung cho hierarchy ro va scan nhanh |
| Top 20 Raise Repositories in Week | Lollipop chart | Delta leaderboard cards | Nhac vao momentum thay vi quy mo |
| Top 20 Language | Treemap | Horizontal bars | Treemap hop khi can show share of market |
| Top 20 Categories | Bubble pack | Donut + ranked list | Tao cam giac "market map" noi bat hon table |
| Topic rotation | Heatmap | Delta matrix | The hien su dich chuyen theo thoi gian |
| Repo drilldown | Line chart | Sparkline list | Phu hop cho progression theo ngay |

## Detailed UX Notes

### 1. Top 20 Repositories

Khoi nay khong nen chi show:

- repo name
- stars
- forks

Khoi nay nen show:

- rank
- repo name
- category chip
- total stars
- weekly raise
- tiny sparkline 7d

Interaction:

- hover: highlight repo
- click: mo drilldown panel
- toggle:
  - `By total stars`
  - `By weekly raise`
  - `By engagement`

### 2. Top 20 Language

Neu user muon scan nhanh thi:

- horizontal bar chart tot hon pie chart

Neu user muon feel duoc "market composition" thi:

- treemap hop ly hon bang

Khuyen nghi:

- default la treemap
- co switch sang list view

### 3. Top 20 Raise Repositories in Week

Day la khoi can duoc nhan manh nhat ve product value.

Nen show:

- star delta week
- percent gain week-over-week
- baseline stars
- badge category

Can tranh:

- tron lan voi top repos theo tong stars

### 4. Top 20 Categories

Vi category level thuong it item hon repo va language, day la noi phu hop de lam visual "showcase".

De xuat:

- bubble pack cho tong quan
- ben phai co ranked legend

Moi category bubble co:

- ten category
- repo count
- weekly growth

### 5. Search

Search can duoc doi ten thanh `Discovery Search` hoac `Explore by Use Case`.

Can co:

- query input
- language filter
- star floor
- result count
- retrieval mode badge

Can co trang thai UX ro:

- idle
- loading
- no result
- degraded mode

`Degraded mode` rat quan trong:

- neu semantic search khong san sang thi van lexical search
- UI can thong bao ro dang chay lexical only, khong duoc fail im lang

## Search Failure Notes

Current state cho thay can kiem tra it nhat 3 diem truoc khi implementation:

1. Frontend hook `useAISearch` dang thieu.
2. Search panel chua duoc gan vao page shell hien tai.
3. Can verify composition root backend dang expose route `/ai/search` dung nhu frontend ky vong.

Neu khong giai quyet 3 diem nay truoc, search khong nen duoc xem la feature da xong.

## Proposed Implementation Scope

### Phase 1: Make the dashboard product-readable

Muc tieu:

- thay table-centric layout bang insight-centric layout
- dat lai thu tu thong tin
- giu nguyen du lieu nen de giam rui ro

Tac dong du kien:

- [frontend/app/page.tsx](/home/iec/lamnh/github/frontend/app/page.tsx)
- [frontend/components/dashboard/TopReposTable.tsx](/home/iec/lamnh/github/frontend/components/dashboard/TopReposTable.tsx)
- [frontend/components/dashboard/TrendingRepos.tsx](/home/iec/lamnh/github/frontend/components/dashboard/TrendingRepos.tsx)
- them component moi cho bar ranking / treemap / bubble chart

### Phase 2: Fix and promote search

Muc tieu:

- khoi phuc search flow end-to-end
- dua search len thanh mot discovery surface dung nghia

Tac dong du kien:

- them `frontend/hooks/useAISearch.ts`
- cap nhat [frontend/lib/api.ts](/home/iec/lamnh/github/frontend/lib/api.ts) neu contract chua khop
- cap nhat [frontend/components/ai/AISearchPanel.tsx](/home/iec/lamnh/github/frontend/components/ai/AISearchPanel.tsx)
- verify [src/presentation/api/ai_routes.py](/home/iec/lamnh/github/src/presentation/api/ai_routes.py)

### Phase 3: Restore dashboard API parity

Muc tieu:

- dam bao source backend co day du dashboard routes ma frontend dang goi

Current risk:

- test suite ky vong dashboard routes ton tai
- source file route hien khong co trong worktree

Tac dong du kien:

- khoi phuc hoac viet lai dashboard composition root
- verify endpoint contract
- bo sung test presentation neu can

## Definition of Done

Dashboard wireframe va implementation duoc xem la dat khi:

- user nhin 5 giay la thay top repo, top raise repo, top language, top categories
- top metrics khong can phai doc bang chi tiet van hieu
- search hoat dong end-to-end
- dashboard co empty/loading/error/degraded states ro rang
- click vao repo co drilldown hop ly
- mobile layout van doc duoc va khong vo thong tin

## Recommendation

Neu dong vai tro developer cho mot san pham thong ke, uu tien dung nen la:

1. Tach ro `Top by size` va `Top by momentum`.
2. Dua search len thanh mot first-class feature, khong de o trang thai phu tro.
3. Giam bang, tang ranking visual va market-map visual.
4. Chi giu table nhu mot secondary toggle cho nhu cau doi chieu chinh xac.

Ket luan:

Du an nay khong thieu data. No dang thieu mot product surface dung de bien data thanh insight. Dashboard moi nen duoc thiet ke nhu mot `market intelligence console`, khong phai mot man hinh dump metric.
