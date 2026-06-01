# BÁO CÁO CUỐI KỲ MÔN DEEP LEARNING

## PHÂN LOẠI REPOSITORY GITHUB THUỘC HỆ SINH THÁI AI/ML BẰNG MÔ HÌNH TRANSFORMER VÀ ỨNG DỤNG TRONG HỆ THỐNG PHÂN TÍCH XU HƯỚNG

---

**Trường:** [Tên trường]  
**Khoa:** [Tên khoa]  
**Môn học:** Deep Learning  
**Giảng viên:** [Tên giảng viên]  
**Nhóm thực hiện:** [Tên nhóm]  
**Thành viên:**  

| STT | Họ và tên | MSSV | Vai trò |
|---|---|---|---|
| 1 | [Họ tên] | [MSSV] | Xây dựng mô hình, thực nghiệm |
| 2 | [Họ tên] | [MSSV] | Thu thập dữ liệu, tiền xử lý |
| 3 | [Họ tên] | [MSSV] | Tích hợp hệ thống, dashboard |

**Thời gian:** [Học kỳ, năm học]

---

## LƯU Ý TRƯỚC KHI NỘP

Tài liệu này là bản báo cáo chi tiết có thể đưa sang Google Docs. Các đoạn đặt trong ngoặc vuông như `[ĐIỀN SỐ LIỆU]`, `[CHÈN HÌNH]` hoặc `[CẬP NHẬT SAU THỰC NGHIỆM]` cần được thay bằng kết quả thực tế trước khi nộp.

Không nên tự điền các chỉ số đẹp nhưng chưa đo. Với môn Deep Learning, một bảng kết quả trung thực, có phân tích hạn chế, thuyết phục hơn một báo cáo có số liệu không thể kiểm chứng.

---

# TÓM TẮT

Sự phát triển nhanh chóng của hệ sinh thái trí tuệ nhân tạo khiến số lượng repository mã nguồn mở trên GitHub tăng mạnh. Các repository này trải rộng trên nhiều nhóm chủ đề như mô hình ngôn ngữ lớn, hệ thống tác tử AI, Retrieval-Augmented Generation, mô hình sinh ảnh, hệ thống đa phương thức và hạ tầng dữ liệu cho AI. Việc theo dõi xu hướng chỉ dựa trên số sao hoặc từ khóa đơn giản chưa đủ để hiểu một repository thuộc nhóm công nghệ nào và đang đóng vai trò gì trong hệ sinh thái.

Báo cáo này trình bày phương pháp phân loại repository GitHub thuộc lĩnh vực AI/ML bằng mô hình Transformer được fine-tune cho bài toán phân loại văn bản nhiều lớp. Dữ liệu đầu vào được tổng hợp từ tên repository, phần mô tả và danh sách topics do GitHub cung cấp. Mỗi repository được gán vào một trong sáu nhóm: `LLM`, `Agent/RAG`, `Diffusion`, `Multimodal`, `Data Engineering` và `Other`.

Để đánh giá vai trò của Deep Learning, nhóm xây dựng và so sánh ba hướng tiếp cận. Phương pháp thứ nhất là hệ luật dựa trên từ khóa, đóng vai trò baseline trực quan. Phương pháp thứ hai sử dụng đặc trưng TF-IDF kết hợp Logistic Regression, đại diện cho Machine Learning truyền thống. Phương pháp thứ ba fine-tune mô hình Transformer pretrained `[DistilBERT / MiniLM / PhoBERT không phù hợp nếu dữ liệu chủ yếu là tiếng Anh - chọn một mô hình thực tế]`. Kết quả thực nghiệm được đánh giá bằng Accuracy, Precision, Recall, Macro-F1 và confusion matrix.

Mô hình sau khi huấn luyện được thiết kế để tích hợp vào hệ thống GitHub AI Trend Analyzer. Hệ thống thu thập dữ liệu GitHub, xử lý luồng sự kiện, lưu trữ metadata và cung cấp dashboard theo dõi xu hướng. Nhờ đó, kết quả của mô hình không chỉ dừng ở một notebook thử nghiệm mà có thể phục vụ phân tích repository theo thời gian thực.

**Từ khóa:** Deep Learning, Transformer, text classification, GitHub repository, fine-tuning, AI trend analysis.

---

# 1. GIỚI THIỆU

## 1.1. Bối cảnh

GitHub là một trong những nền tảng quan trọng nhất đối với cộng đồng phát triển phần mềm mã nguồn mở. Trong lĩnh vực AI/ML, các mô hình, framework, công cụ hỗ trợ và bộ dữ liệu mới thường được công bố hoặc phát triển công khai trên GitHub. Một số repository có thể tăng nhanh hàng nghìn lượt quan tâm trong thời gian ngắn, phản ánh sự dịch chuyển của xu hướng công nghệ.

Tuy nhiên, việc theo dõi repository nổi bật không chỉ là bài toán sắp xếp theo số sao. Một repository về mô hình ngôn ngữ lớn có ý nghĩa khác với một vector database, một framework xây dựng agent hoặc một công cụ sinh ảnh. Nếu chỉ quan sát tổng số stars, người dùng khó trả lời các câu hỏi như:

- Nhóm công nghệ AI nào đang tăng trưởng nhanh?
- Repository mới nổi thuộc nhóm LLM, Agent/RAG hay Diffusion?
- Các chủ đề nào đang được cộng đồng quan tâm nhiều hơn trong tuần gần nhất?
- Có thể tự động phân loại repository mới mà không cần cập nhật thủ công danh sách từ khóa hay không?

Từ nhu cầu đó, nhóm xây dựng bài toán phân loại repository GitHub theo nhóm AI/ML bằng mô hình Deep Learning cho văn bản.

## 1.2. Vấn đề của phương pháp dựa trên từ khóa

Một cách tiếp cận đơn giản là tạo danh sách từ khóa và gán nhãn theo luật. Ví dụ, repository có topic `llm`, `transformer` hoặc `fine-tuning` có thể được xếp vào nhóm `LLM`; repository có topic `rag`, `agent` hoặc `langchain` có thể được xếp vào nhóm `Agent/RAG`.

Phương pháp này có ba ưu điểm: dễ hiểu, tốc độ nhanh và không cần dữ liệu huấn luyện. Tuy nhiên, nó tồn tại nhiều hạn chế:

- Cần cập nhật thủ công khi xuất hiện công nghệ hoặc thuật ngữ mới.
- Không hiểu ngữ cảnh. Ví dụ, từ `agent` có thể xuất hiện trong một repository không liên quan đến AI agent.
- Khó nhận diện các mô tả có ý nghĩa tương đương nhưng không chứa đúng từ khóa.
- Dễ phụ thuộc vào thứ tự luật khi một repository thuộc nhiều nhóm chủ đề.
- Không học được từ các ví dụ đã gán nhãn.

Các hạn chế này tạo ra động lực sử dụng Transformer, một kiến trúc Deep Learning có khả năng biểu diễn ngữ nghĩa của văn bản theo ngữ cảnh.

## 1.3. Mục tiêu

Mục tiêu chính của đề tài là xây dựng mô hình phân loại repository GitHub theo nhóm AI/ML từ dữ liệu văn bản và tích hợp mô hình vào một hệ thống phân tích xu hướng.

Các mục tiêu cụ thể:

1. Xây dựng tập dữ liệu repository GitHub có nhãn.
2. Tiền xử lý và tổng hợp thông tin văn bản từ metadata của repository.
3. Cài đặt baseline dựa trên luật và baseline Machine Learning truyền thống.
4. Fine-tune một mô hình Transformer pretrained cho bài toán phân loại nhiều lớp.
5. So sánh các mô hình bằng metric phù hợp và phân tích lỗi.
6. Thiết kế cách tích hợp mô hình vào pipeline phân tích xu hướng hiện có.

## 1.4. Câu hỏi nghiên cứu

Báo cáo tập trung trả lời các câu hỏi sau:

1. Mô hình Transformer có cải thiện chất lượng phân loại so với hệ luật thủ công hay không?
2. Mô hình Deep Learning có xử lý tốt hơn các repository thiếu topic nhưng có mô tả giàu ngữ nghĩa hay không?
3. Những nhóm nào dễ bị nhầm lẫn với nhau?
4. Việc bổ sung topics vào description có giúp tăng chất lượng phân loại hay không?
5. Mô hình có đủ nhẹ để tích hợp vào pipeline ứng dụng thực tế hay không?

## 1.5. Phạm vi

Đề tài tập trung vào phân loại văn bản ngắn từ GitHub repository metadata. Nội dung đầu vào chính gồm:

- Tên repository.
- Tên owner.
- Mô tả repository.
- GitHub topics.
- `[TÙY CHỌN]` Phần đầu README đã được cắt ngắn.

Đề tài không huấn luyện Transformer từ đầu do giới hạn tài nguyên. Thay vào đó, nhóm sử dụng transfer learning: khởi tạo từ mô hình pretrained và fine-tune trên tập dữ liệu của bài toán.

---

# 2. CƠ SỞ LÝ THUYẾT

## 2.1. Bài toán phân loại văn bản nhiều lớp

Cho tập dữ liệu:

`D = {(x_i, y_i)} với i = 1, 2, ..., N`

Trong đó:

- `x_i` là văn bản mô tả repository thứ `i`.
- `y_i` là nhãn thuộc một trong `K = 6` lớp.

Mục tiêu là học hàm:

`f(x_i) -> y_i`

để dự đoán đúng nhãn cho repository chưa xuất hiện trong dữ liệu huấn luyện.

Các lớp trong đề tài:

| Nhãn | Ý nghĩa | Ví dụ tín hiệu |
|---|---|---|
| `LLM` | Mô hình ngôn ngữ lớn, inference, fine-tuning | transformer, llama, language model |
| `Agent/RAG` | Tác tử AI, orchestration, retrieval | agent, rag, langchain |
| `Diffusion` | Sinh ảnh, sinh video, diffusion model | stable diffusion, text-to-image |
| `Multimodal` | Vision-language, audio, speech, OCR | multimodal, VLM, speech |
| `Data Engineering` | Vector DB, embedding, dataset, MLOps | vector search, embedding, dataset |
| `Other` | Repository chưa thuộc các nhóm trên | các công cụ hoặc nội dung khác |

## 2.2. Biểu diễn văn bản truyền thống với TF-IDF

TF-IDF biểu diễn văn bản thành vector dựa trên tần suất từ. Với từ `t` trong tài liệu `d`:

`TF-IDF(t, d) = TF(t, d) * IDF(t)`

Trong đó:

`IDF(t) = log(N / (1 + df(t)))`

TF-IDF là baseline hữu ích vì đơn giản, nhanh và thường hoạt động tốt khi từ khóa phân biệt giữa các lớp rõ ràng. Hạn chế của phương pháp là không hiểu thứ tự từ và ngữ cảnh. Hai cụm từ gần nghĩa nhưng dùng từ khác nhau có thể được biểu diễn rất khác nhau.

## 2.3. Embedding và biểu diễn ngữ nghĩa

Embedding ánh xạ từ hoặc câu sang vector số thực trong không gian nhiều chiều. Các văn bản có nội dung gần nhau thường có vector gần nhau theo cosine similarity:

`cosine_similarity(a, b) = (a . b) / (||a|| * ||b||)`

Khác với TF-IDF, embedding từ mô hình pretrained có thể nắm bắt quan hệ ngữ nghĩa. Ví dụ, mô tả `"framework for retrieval augmented applications"` có thể gần với khái niệm `RAG` dù không dùng đúng từ viết tắt.

## 2.4. Kiến trúc Transformer

Transformer sử dụng cơ chế self-attention để xác định mức độ liên quan giữa các token trong cùng chuỗi đầu vào. Với ba ma trận Query, Key và Value:

`Attention(Q, K, V) = softmax(QK^T / sqrt(d_k))V`

Self-attention giúp mô hình xem xét ngữ cảnh toàn cục thay vì xử lý tuần tự như RNN hoặc LSTM. Transformer cũng hỗ trợ huấn luyện song song hiệu quả hơn trên GPU.

Mỗi encoder block thường gồm:

1. Multi-head self-attention.
2. Add & Layer Normalization.
3. Feed-forward neural network.
4. Add & Layer Normalization.

`[CHÈN HÌNH 1: Sơ đồ Transformer Encoder hoặc sơ đồ mô hình classifier]`

## 2.5. Fine-tuning mô hình pretrained

Huấn luyện một Transformer từ đầu cần dữ liệu và tài nguyên tính toán lớn. Vì vậy, đề tài sử dụng transfer learning:

1. Tải mô hình pretrained đã học biểu diễn ngôn ngữ tổng quát.
2. Thêm classification head gồm một lớp tuyến tính.
3. Fine-tune toàn bộ hoặc một phần tham số trên dữ liệu repository.
4. Dùng softmax để thu được xác suất cho từng lớp.

Với vector đại diện đầu ra `h`:

`z = Wh + b`

`p(y = c | x) = softmax(z_c)`

Nhãn dự đoán:

`y_hat = argmax_c p(y = c | x)`

## 2.6. Hàm mất mát

Với bài toán phân loại nhiều lớp, hàm Cross Entropy Loss được sử dụng:

`L = - sum(y_c * log(p_c))`

Nếu dữ liệu mất cân bằng, có thể dùng trọng số theo lớp:

`L_weighted = - sum(w_c * y_c * log(p_c))`

Trong đó `w_c` lớn hơn đối với lớp ít mẫu hơn.

## 2.7. Các metric đánh giá

### Accuracy

Tỷ lệ mẫu được dự đoán đúng:

`Accuracy = số dự đoán đúng / tổng số mẫu`

### Precision

Trong các mẫu được dự đoán thuộc lớp `c`, tỷ lệ mẫu thực sự thuộc lớp `c`:

`Precision = TP / (TP + FP)`

### Recall

Trong các mẫu thực sự thuộc lớp `c`, tỷ lệ mẫu được nhận diện đúng:

`Recall = TP / (TP + FN)`

### F1-score

Trung bình điều hòa giữa Precision và Recall:

`F1 = 2 * Precision * Recall / (Precision + Recall)`

### Macro-F1

Macro-F1 là trung bình F1 của tất cả các lớp, không phụ thuộc lớp đó có nhiều hay ít mẫu. Đây là metric quan trọng khi dữ liệu mất cân bằng:

`Macro-F1 = (1 / K) * sum(F1_c)`

---

# 3. PHÂN TÍCH BÀI TOÁN VÀ DỮ LIỆU

## 3.1. Nguồn dữ liệu

Dữ liệu repository được thu thập từ GitHub API. Mỗi repository có thể chứa các trường:

| Trường | Mô tả | Sử dụng trong mô hình |
|---|---|---|
| `repo_name` | Tên repository | Có |
| `repo_full_name` | Owner và tên repository | Có |
| `description` | Mô tả ngắn | Có |
| `topics` | Danh sách chủ đề | Có |
| `language` | Ngôn ngữ lập trình chính | Tùy chọn |
| `stargazers_count` | Số sao | Không dùng làm đặc trưng ngữ nghĩa chính |
| `forks_count` | Số lượt fork | Không dùng làm đặc trưng ngữ nghĩa chính |
| `readme_text` | Nội dung README | Tùy chọn trong ablation study |

Không nên đưa số stars trực tiếp vào mô hình phân loại chủ đề ở thí nghiệm chính. Stars phản ánh độ phổ biến, không phản ánh bản chất nội dung. Việc tách hai loại tín hiệu giúp kết quả dễ giải thích hơn.

## 3.2. Xây dựng văn bản đầu vào

Văn bản đầu vào có thể được tổng hợp theo định dạng:

```text
[NAME] huggingface/transformers
[TOPICS] transformer, pytorch, pretrained-models, natural-language-processing
[DESCRIPTION] Transformers: state-of-the-art machine learning for PyTorch, TensorFlow, and JAX.
```

Định dạng có tag giúp mô hình phân biệt nguồn thông tin. Khi dùng tokenizer của Transformer, chuỗi sẽ được cắt ở độ dài tối đa `[128 / 256]` tokens.

## 3.3. Phương pháp gán nhãn

Để có tập dữ liệu đáng tin cậy, nhóm đề xuất quy trình gán nhãn hai giai đoạn:

1. **Gán nhãn sơ bộ:** dùng topics và hệ luật để tạo nhãn ban đầu.
2. **Kiểm tra thủ công:** rà soát các mẫu ngẫu nhiên, mẫu có nhiều tín hiệu xung đột và mẫu thuộc lớp ít dữ liệu.

Nếu có nhiều thành viên, nên dùng hai người gán nhãn độc lập cho một phần dữ liệu và tính mức độ đồng thuận. Các trường hợp bất đồng được thảo luận để đưa ra nhãn cuối.

Nguyên tắc gán nhãn:

- Chọn nhóm thể hiện chức năng chính của repository.
- Không gán `LLM` chỉ vì repository có ví dụ sử dụng LLM nếu chức năng chính là vector database.
- Chọn `Agent/RAG` khi repository tập trung orchestration, retrieval workflow hoặc agent framework.
- Chọn `Data Engineering` khi chức năng chính là lưu trữ, embedding, vector search, dataset hoặc MLOps.
- Dùng `Other` nếu không đủ bằng chứng hoặc repository không thuộc AI/ML.

## 3.4. Phân chia dữ liệu

Tập dữ liệu được chia theo tỷ lệ:

| Tập | Tỷ lệ đề xuất | Mục đích |
|---|---:|---|
| Train | 70% | Cập nhật trọng số mô hình |
| Validation | 15% | Chọn hyperparameter và theo dõi overfitting |
| Test | 15% | Đánh giá cuối cùng |

Nên dùng stratified split để giữ tỷ lệ lớp tương đối ổn định. Nếu có nhiều snapshot của cùng repository, phải bảo đảm một repository không xuất hiện đồng thời trong train và test để tránh data leakage.

## 3.5. Thống kê dữ liệu

`[CHÈN BẢNG SAU KHI TẠO DATASET]`

| Nhãn | Train | Validation | Test | Tổng |
|---|---:|---:|---:|---:|
| LLM | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] |
| Agent/RAG | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] |
| Diffusion | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] |
| Multimodal | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] |
| Data Engineering | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] |
| Other | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] |
| **Tổng** | **[ĐIỀN]** | **[ĐIỀN]** | **[ĐIỀN]** | **[ĐIỀN]** |

`[CHÈN HÌNH 2: Biểu đồ cột phân bố số mẫu theo nhãn]`

## 3.6. Tiền xử lý dữ liệu

Quy trình tiền xử lý:

1. Loại bỏ repository thiếu toàn bộ tên, mô tả và topics.
2. Chuẩn hóa khoảng trắng.
3. Ghép `name`, `topics` và `description` theo định dạng thống nhất.
4. Loại bỏ bản ghi trùng theo `repo_full_name`.
5. Chia train, validation và test theo repository.
6. Tokenize bằng tokenizer đi kèm mô hình pretrained.
7. Padding và truncation về độ dài tối đa.

Không nên xóa toàn bộ ký tự đặc biệt một cách máy móc. Các token như `C++`, `.NET`, `Llama-3`, `text-to-image` hoặc tên framework có thể chứa thông tin hữu ích.

---

# 4. PHƯƠNG PHÁP ĐỀ XUẤT

## 4.1. Tổng quan

Đề tài so sánh ba cấp độ mô hình:

| Mô hình | Vai trò | Đặc điểm |
|---|---|---|
| Rule-based classifier | Baseline 1 | Nhanh, dễ hiểu, không cần train |
| TF-IDF + Logistic Regression | Baseline 2 | Machine Learning truyền thống |
| Fine-tuned Transformer | Mô hình đề xuất | Hiểu ngữ cảnh tốt hơn |

Việc so sánh này giúp trả lời câu hỏi quan trọng: Deep Learning mang lại cải thiện thực tế như thế nào so với các giải pháp đơn giản hơn?

## 4.2. Baseline 1: Phân loại dựa trên luật

Hệ luật sử dụng danh sách topics và keyword theo từng lớp. Ví dụ:

| Lớp | Một số keyword |
|---|---|
| LLM | llm, transformer, llama, fine-tuning |
| Agent/RAG | agent, rag, langchain, retrieval |
| Diffusion | diffusion, text-to-image, stable diffusion |
| Multimodal | multimodal, vision-language, speech |
| Data Engineering | vector-db, embedding, dataset, mlops |

Nếu nhiều nhóm cùng khớp, hệ luật dùng thứ tự ưu tiên cố định. Nếu không có keyword nào khớp, repository được xếp vào `Other`.

Baseline này phản ánh cách giải quyết ban đầu trong ứng dụng. Đây cũng là mốc so sánh quan trọng vì mô hình Deep Learning chỉ có ý nghĩa khi giải quyết được các trường hợp hệ luật bỏ sót hoặc gán sai.

## 4.3. Baseline 2: TF-IDF và Logistic Regression

Văn bản đầu vào được chuyển thành TF-IDF vector. Sau đó Logistic Regression dự đoán xác suất thuộc từng lớp.

Hyperparameter đề xuất:

| Tham số | Giá trị khởi đầu |
|---|---|
| N-gram | `(1, 2)` |
| Số đặc trưng tối đa | `20,000` |
| Regularization | `L2` |
| Class weight | `balanced` |
| Số vòng lặp tối đa | `1,000` |

Baseline này thường mạnh trên dữ liệu text classification nhỏ. Nếu Transformer không cải thiện đáng kể, cần phân tích nguyên nhân thay vì mặc định Deep Learning luôn tốt hơn.

## 4.4. Mô hình Transformer đề xuất

### 4.4.1. Lựa chọn mô hình

Mô hình khuyến nghị cho bài toán là `distilbert-base-uncased` hoặc `sentence-transformers/all-MiniLM-L6-v2`.

Trong báo cáo chính, nên chọn **một** mô hình đã thực sự huấn luyện:

- `distilbert-base-uncased`: phù hợp nếu ưu tiên quy trình fine-tuning phân loại văn bản kinh điển, dễ giải thích trong môn Deep Learning.
- `all-MiniLM-L6-v2`: nhẹ hơn, thuận lợi nếu muốn tái sử dụng embedding cho semantic search.

Nếu dữ liệu mô tả repository chủ yếu bằng tiếng Anh, không nên chọn PhoBERT chỉ vì nhóm sử dụng tiếng Việt trong báo cáo.

### 4.4.2. Kiến trúc

Pipeline dự đoán:

```text
Repository metadata
        |
        v
Ghép name + topics + description
        |
        v
Tokenizer
        |
        v
Transformer Encoder
        |
        v
Vector đại diện [CLS] hoặc pooled output
        |
        v
Dropout
        |
        v
Linear Layer: hidden_size -> 6 classes
        |
        v
Softmax probabilities
        |
        v
Predicted category
```

`[CHÈN HÌNH 3: Sơ đồ kiến trúc mô hình đề xuất]`

### 4.4.3. Classification head

Classification head gồm:

1. Pooled embedding từ Transformer.
2. Dropout để giảm overfitting.
3. Fully connected layer ánh xạ sang sáu lớp.
4. Softmax khi inference.

Trong quá trình training, Cross Entropy Loss được tính trực tiếp từ logits.

## 4.5. Quy trình huấn luyện

Quy trình huấn luyện đề xuất:

1. Chuẩn bị train, validation và test set.
2. Tokenize dữ liệu theo batch.
3. Khởi tạo pretrained Transformer.
4. Fine-tune với optimizer AdamW.
5. Theo dõi validation loss và Macro-F1 sau mỗi epoch.
6. Lưu checkpoint tốt nhất theo validation Macro-F1.
7. Đánh giá checkpoint tốt nhất trên test set.

Pseudocode:

```text
best_macro_f1 = 0

for epoch in range(num_epochs):
    model.train()
    for batch in train_loader:
        logits = model(batch.input_ids, batch.attention_mask)
        loss = cross_entropy(logits, batch.labels)
        loss.backward()
        optimizer.step()
        scheduler.step()
        optimizer.zero_grad()

    val_macro_f1 = evaluate(model, validation_loader)
    if val_macro_f1 > best_macro_f1:
        save_checkpoint(model)
        best_macro_f1 = val_macro_f1
```

## 4.6. Hyperparameter

`[CẬP NHẬT THEO CẤU HÌNH ĐÃ CHẠY]`

| Hyperparameter | Giá trị đề xuất |
|---|---|
| Pretrained model | `distilbert-base-uncased` |
| Max sequence length | `128` |
| Batch size | `16` |
| Epochs | `3-5` |
| Optimizer | `AdamW` |
| Learning rate | `2e-5` |
| Weight decay | `0.01` |
| Dropout | `0.1` |
| Warmup ratio | `0.1` |
| Loss | Weighted Cross Entropy nếu dữ liệu lệch lớp |
| Random seed | `42` |

## 4.7. Xử lý mất cân bằng dữ liệu

Dữ liệu GitHub có thể không cân bằng. Ví dụ, nhóm `LLM` thường có nhiều repository hơn `Diffusion` hoặc `Multimodal`. Nếu chỉ tối ưu Accuracy, mô hình có thể ưu tiên lớp phổ biến.

Các biện pháp:

- Dùng Macro-F1 làm metric chính.
- Dùng stratified split.
- Sử dụng class weights trong loss.
- Theo dõi Precision và Recall theo từng lớp.
- `[TÙY CHỌN]` Thử oversampling lớp ít dữ liệu trong train set.

## 4.8. Tích hợp semantic search như phần mở rộng

Sau khi có Transformer encoder, nhóm có thể mở rộng sang semantic search:

1. Sinh embedding cho từng repository.
2. Sinh embedding cho câu truy vấn người dùng.
3. Tính cosine similarity.
4. Kết hợp semantic score với lexical score và popularity score.

Công thức tổng quát:

`FinalScore = alpha * SemanticScore + beta * LexicalScore + gamma * PopularityScore`

Trong đó:

`alpha + beta + gamma = 1`

Ví dụ khởi đầu:

`alpha = 0.55, beta = 0.30, gamma = 0.15`

Phần semantic search nên được trình bày là phần mở rộng nếu nhóm chưa triển khai và đo lường đầy đủ. Trọng tâm Deep Learning chính của báo cáo vẫn là Transformer classifier.

---

# 5. THỰC NGHIỆM VÀ ĐÁNH GIÁ

## 5.1. Môi trường thực nghiệm

`[CẬP NHẬT THEO MÁY THỰC TẾ]`

| Thành phần | Cấu hình |
|---|---|
| Hệ điều hành | [Windows / Ubuntu / Google Colab] |
| CPU | [ĐIỀN] |
| GPU | [ĐIỀN, ví dụ NVIDIA T4 16 GB] |
| RAM | [ĐIỀN] |
| Python | [ĐIỀN] |
| PyTorch | [ĐIỀN] |
| Transformers | [ĐIỀN] |
| Scikit-learn | [ĐIỀN] |

Nếu sử dụng Google Colab, cần ghi rõ loại GPU được cấp trong lần chạy thực nghiệm cuối.

## 5.2. Kịch bản thực nghiệm

Các thí nghiệm tối thiểu:

| Mã | Mục tiêu |
|---|---|
| E1 | Đánh giá rule-based classifier |
| E2 | Đánh giá TF-IDF + Logistic Regression |
| E3 | Đánh giá Transformer fine-tuning |
| E4 | So sánh `description` với `name + topics + description` |
| E5 | Đo thời gian inference trung bình |

Nếu còn thời gian:

| Mã | Mục tiêu |
|---|---|
| E6 | So sánh DistilBERT với MiniLM |
| E7 | So sánh có và không dùng class weights |
| E8 | Thử thêm đoạn đầu README |

## 5.3. Kết quả tổng quan

`[CHỈ ĐIỀN SAU KHI CHẠY THỰC NGHIỆM]`

| Mô hình | Accuracy | Macro Precision | Macro Recall | Macro-F1 | Inference ms/mẫu |
|---|---:|---:|---:|---:|---:|
| Rule-based | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] |
| TF-IDF + Logistic Regression | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] |
| Fine-tuned Transformer | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] |

Đoạn nhận xét mẫu sau khi có số liệu:

> Mô hình Transformer đạt Macro-F1 là `[ĐIỀN]`, cao hơn `[ĐIỀN]` điểm phần trăm so với rule-based classifier và `[ĐIỀN]` điểm phần trăm so với TF-IDF + Logistic Regression. Kết quả cho thấy biểu diễn ngữ nghĩa theo ngữ cảnh giúp mô hình xử lý tốt hơn các repository không chứa keyword trực tiếp. Tuy nhiên, thời gian inference tăng từ `[ĐIỀN]` ms lên `[ĐIỀN]` ms mỗi mẫu, tạo ra đánh đổi giữa chất lượng và chi phí tính toán.

## 5.4. Kết quả theo từng lớp

`[CHỈ ĐIỀN SAU KHI CHẠY THỰC NGHIỆM]`

| Lớp | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| LLM | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] |
| Agent/RAG | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] |
| Diffusion | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] |
| Multimodal | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] |
| Data Engineering | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] |
| Other | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] |

`[CHÈN HÌNH 4: Confusion matrix của Transformer trên test set]`

## 5.5. Đường cong huấn luyện

`[CHÈN HÌNH 5: Train loss và validation loss theo epoch]`  
`[CHÈN HÌNH 6: Validation Macro-F1 theo epoch]`

Nội dung cần phân tích:

- Loss có giảm ổn định hay không?
- Validation loss có tăng trở lại sau một số epoch hay không?
- Checkpoint tốt nhất nằm ở epoch nào?
- Có dấu hiệu overfitting không?

Đoạn nhận xét mẫu:

> Training loss giảm dần qua các epoch, trong khi validation Macro-F1 đạt cao nhất tại epoch `[ĐIỀN]`. Sau thời điểm này, `[validation loss tăng nhẹ / metric ổn định / chưa quan sát overfitting rõ rệt]`. Vì vậy, nhóm lựa chọn checkpoint tại epoch `[ĐIỀN]` cho đánh giá cuối cùng.

## 5.6. Ablation study: ảnh hưởng của trường đầu vào

Mục tiêu của ablation study là xác định nguồn thông tin nào đóng góp nhiều nhất.

`[CHỈ ĐIỀN SAU KHI CHẠY]`

| Input | Accuracy | Macro-F1 |
|---|---:|---:|
| Description | [ĐIỀN] | [ĐIỀN] |
| Name + Description | [ĐIỀN] | [ĐIỀN] |
| Topics + Description | [ĐIỀN] | [ĐIỀN] |
| Name + Topics + Description | [ĐIỀN] | [ĐIỀN] |
| `[TÙY CHỌN]` Name + Topics + Description + README | [ĐIỀN] | [ĐIỀN] |

Đoạn nhận xét mẫu:

> Khi chỉ sử dụng description, mô hình đạt Macro-F1 `[ĐIỀN]`. Việc bổ sung topics giúp metric tăng lên `[ĐIỀN]`, cho thấy topics là tín hiệu cô đọng và có giá trị. Tuy nhiên, mô hình vẫn cần description để xử lý repository có topics thiếu hoặc không đồng nhất.

## 5.7. Phân tích lỗi

Phân tích lỗi là phần quan trọng vì cho thấy nhóm hiểu giới hạn mô hình thay vì chỉ báo cáo metric.

`[ĐIỀN 5-10 VÍ DỤ THỰC TẾ]`

| Repository | Nhãn đúng | Dự đoán | Phân tích nguyên nhân |
|---|---|---|---|
| [repo 1] | Agent/RAG | LLM | Repository dùng LLM nhưng chức năng chính là agent orchestration |
| [repo 2] | Data Engineering | Agent/RAG | Description nhắc RAG nhiều hơn chức năng vector storage |
| [repo 3] | Multimodal | LLM | Mô tả ngắn, thiếu topic vision-language |
| [repo 4] | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] |
| [repo 5] | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] |

Các nhóm dễ nhầm lẫn dự kiến:

- `LLM` và `Agent/RAG`: agent thường sử dụng LLM làm nền tảng.
- `Agent/RAG` và `Data Engineering`: RAG liên quan embedding và vector database.
- `Diffusion` và `Multimodal`: repository có thể xử lý cả ảnh, video và text.
- `Other` và các lớp chuyên biệt: mô tả quá ngắn hoặc thiếu topics.

## 5.8. So sánh định tính

Ví dụ minh họa nên chọn các repository mà rule-based không nhận ra nhưng Transformer dự đoán đúng.

`[ĐIỀN SAU KHI CHẠY MÔ HÌNH]`

| Input rút gọn | Rule-based | Transformer | Nhận xét |
|---|---|---|---|
| "framework for building retrieval augmented applications" | Other | Agent/RAG | Transformer hiểu quan hệ ngữ nghĩa với RAG |
| "high-performance similarity search engine for embeddings" | Other hoặc Data Engineering | Data Engineering | Mô hình nhận diện ý nghĩa vector search |
| [Ví dụ thực tế] | [ĐIỀN] | [ĐIỀN] | [ĐIỀN] |

## 5.9. Thảo luận

Sau khi có số liệu, phần thảo luận nên trả lời:

1. Deep Learning cải thiện metric nào rõ nhất?
2. Cải thiện có đến từ lớp ít dữ liệu hay chỉ lớp phổ biến?
3. Transformer có đáng dùng trong production so với TF-IDF không?
4. Khi nào hệ luật vẫn hữu ích?

Một kết luận hợp lý thường không phải "Transformer thay thế hoàn toàn rule-based". Thiết kế thực tế có thể kết hợp:

- Rule-based cho các trường hợp topic rõ ràng và cần latency cực thấp.
- Transformer cho repository mới, thiếu topic hoặc có nhiều tín hiệu mơ hồ.
- Confidence threshold để chuyển các mẫu không chắc chắn sang kiểm tra thủ công.

---

# 6. TÍCH HỢP VÀO HỆ THỐNG GITHUB AI TREND ANALYZER

## 6.1. Tổng quan ứng dụng

GitHub AI Trend Analyzer là hệ thống thu thập và phân tích hoạt động repository từ GitHub. Hệ thống hướng đến việc theo dõi repository nổi bật, xu hướng topic và biến động mức độ quan tâm theo thời gian.

Luồng xử lý tổng quát:

```text
GitHub API
    |
    v
Thu thập repository metadata và events
    |
    v
Kafka
    |
    v
Spark Structured Streaming
    |
    +--------------------+
    |                    |
    v                    v
ClickHouse             Parquet
    |
    v
FastAPI
    |
    v
Next.js Dashboard
```

`[CHÈN HÌNH 7: Sơ đồ kiến trúc tổng thể ứng dụng]`

## 6.2. Vị trí của mô hình Deep Learning

Mô hình Transformer được đặt tại bước enrichment metadata:

```text
Repository metadata
        |
        v
Text preprocessing
        |
        v
Transformer classifier
        |
        +--> predicted_category
        +--> confidence_score
        |
        v
Lưu vào ClickHouse
        |
        v
Dashboard category analytics
```

Phân loại không nhất thiết phải chạy trên mọi GitHub event. Một repository có thể phát sinh nhiều event nhưng metadata thay đổi ít hơn. Vì vậy, thiết kế hợp lý là:

1. Chỉ inference khi repository mới xuất hiện.
2. Inference lại khi description hoặc topics thay đổi.
3. Cache kết quả phân loại theo `repo_full_name` và phiên bản metadata.
4. Chạy batch enrichment định kỳ cho repository chưa có nhãn.

Thiết kế này giảm chi phí inference và phù hợp với pipeline dữ liệu lớn.

## 6.3. API dự đoán đề xuất

API nội bộ:

```http
POST /ml/classify-repository
Content-Type: application/json
```

Request:

```json
{
  "repo_full_name": "owner/repository",
  "description": "A framework for building retrieval augmented AI applications",
  "topics": ["retrieval", "agents", "llm"]
}
```

Response:

```json
{
  "category": "Agent/RAG",
  "confidence": 0.91,
  "model_version": "distilbert-repo-classifier-v1"
}
```

## 6.4. Chiến lược triển khai

Có hai phương án:

| Phương án | Ưu điểm | Nhược điểm |
|---|---|---|
| Nhúng model trong FastAPI hiện tại | Đơn giản, phù hợp demo | API analytics phải mang thêm model |
| Tách model-serving service | Dễ scale, tách trách nhiệm | Tăng độ phức tạp triển khai |

Với phạm vi môn học, có thể dùng phương án nhúng model hoặc một service FastAPI nhỏ. Với production, model-serving service riêng hợp lý hơn.

## 6.5. Dashboard

Dashboard có thể sử dụng nhãn dự đoán để hiển thị:

- Phân bố repository theo category.
- Top repository trong từng category.
- Category tăng trưởng nhanh theo thời gian.
- Repository có confidence thấp cần xem lại.
- So sánh xu hướng `LLM`, `Agent/RAG`, `Diffusion`, `Multimodal` và `Data Engineering`.

`[CHÈN HÌNH 8: Screenshot dashboard hiện tại hoặc mockup dashboard có category]`

## 6.6. Giám sát mô hình

Khi đưa mô hình vào hệ thống, cần theo dõi:

- Inference latency.
- Số repository được phân loại mỗi giờ.
- Tỷ lệ confidence thấp.
- Phân bố nhãn theo thời gian.
- Data drift: từ khóa và framework mới xuất hiện.
- Model version đang phục vụ.

Nếu tỷ lệ `Other` tăng bất thường hoặc confidence giảm dần, tập dữ liệu huấn luyện có thể đã lỗi thời.

---

# 7. HẠN CHẾ VÀ HƯỚNG PHÁT TRIỂN

## 7.1. Hạn chế

### Chất lượng nhãn

Nhãn ban đầu có thể được suy ra từ topics và keyword, sau đó mới kiểm tra thủ công. Vì vậy, dữ liệu vẫn có nguy cơ chứa nhiễu. Một số repository thực tế thuộc nhiều nhóm nhưng bài toán hiện tại buộc chọn một nhãn duy nhất.

### Dữ liệu thay đổi nhanh

Hệ sinh thái AI thay đổi liên tục. Framework và thuật ngữ mới xuất hiện có thể khiến mô hình suy giảm chất lượng theo thời gian.

### Mất cân bằng lớp

Các nhóm như LLM và Agent/RAG có thể chiếm nhiều mẫu hơn Diffusion hoặc Multimodal. Điều này ảnh hưởng Recall của lớp ít dữ liệu.

### Chi phí inference

Transformer chậm hơn rule-based và TF-IDF. Khi số lượng repository lớn, hệ thống cần batch inference, caching hoặc model quantization.

### Bài toán single-label

Một repository có thể vừa cung cấp vector database, vừa hỗ trợ RAG và agent. Trong tương lai, multi-label classification có thể phản ánh đúng thực tế hơn.

## 7.2. Hướng phát triển

### Multi-label classification

Thay softmax bằng sigmoid cho từng lớp và dùng Binary Cross Entropy Loss. Một repository có thể đồng thời nhận nhiều nhãn.

### Active learning

Ưu tiên gán nhãn thủ công cho repository có confidence thấp hoặc mô hình bất đồng với hệ luật. Cách này giảm chi phí tạo dữ liệu.

### Semantic search

Lưu embedding repository vào vector database như Qdrant hoặc pgvector để hỗ trợ tìm kiếm ngữ nghĩa:

```text
"framework nhẹ để fine-tune LLM"
```

thay vì chỉ tìm từ khóa chính xác.

### Model distillation và quantization

Giảm kích thước mô hình để tăng tốc inference trên CPU. Đây là hướng phù hợp nếu ứng dụng cần xử lý repository ở quy mô lớn.

### Theo dõi data drift

Định kỳ lấy mẫu repository mới, đo confidence và phân phối nhãn, sau đó fine-tune lại mô hình khi cần.

---

# 8. KẾT LUẬN

Đề tài xây dựng hướng tiếp cận Deep Learning cho bài toán phân loại repository GitHub thuộc hệ sinh thái AI/ML. Thay vì chỉ dựa trên danh sách từ khóa thủ công, mô hình Transformer được fine-tune để khai thác ngữ cảnh từ tên repository, topics và description.

Thiết kế thực nghiệm so sánh ba phương pháp: rule-based classifier, TF-IDF kết hợp Logistic Regression và Transformer fine-tuning. Sự so sánh này giúp đánh giá rõ giá trị thực tế của Deep Learning, đồng thời chỉ ra đánh đổi giữa chất lượng dự đoán và chi phí inference.

`[CẬP NHẬT SAU THỰC NGHIỆM: Thêm 2-3 câu nêu Macro-F1 tốt nhất, mức cải thiện và lớp còn yếu.]`

Ngoài mô hình, đề tài đặt bài toán vào bối cảnh ứng dụng GitHub AI Trend Analyzer. Mô hình có thể được tích hợp ở bước enrichment metadata, lưu kết quả vào ClickHouse và phục vụ dashboard phân tích xu hướng. Hướng tiếp cận này cho thấy Deep Learning không chỉ là một mô hình thử nghiệm độc lập mà có thể trở thành thành phần hữu ích trong hệ thống phần mềm thực tế.

---

# TÀI LIỆU THAM KHẢO

`[ĐỊNH DẠNG LẠI THEO IEEE HOẶC APA TÙY YÊU CẦU GIẢNG VIÊN]`

1. A. Vaswani et al., "Attention Is All You Need," Advances in Neural Information Processing Systems, 2017.
2. J. Devlin, M.-W. Chang, K. Lee, and K. Toutanova, "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding," NAACL-HLT, 2019.
3. V. Sanh, L. Debut, J. Chaumond, and T. Wolf, "DistilBERT, a distilled version of BERT: smaller, faster, cheaper and lighter," 2019.
4. N. Reimers and I. Gurevych, "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks," EMNLP-IJCNLP, 2019.
5. T. Wolf et al., "Transformers: State-of-the-Art Natural Language Processing," EMNLP: System Demonstrations, 2020.
6. GitHub REST API Documentation, https://docs.github.com/en/rest.
7. Hugging Face Transformers Documentation, https://huggingface.co/docs/transformers.
8. PyTorch Documentation, https://pytorch.org/docs/stable/index.html.

---

# PHỤ LỤC A. CHECKLIST HOÀN THIỆN TRƯỚC KHI NỘP

## Nội dung bắt buộc

- [ ] Điền thông tin trường, giảng viên và thành viên.
- [ ] Chốt pretrained model đã thực sự fine-tune.
- [ ] Ghi rõ cách thu thập và gán nhãn dữ liệu.
- [ ] Điền bảng phân bố dataset.
- [ ] Điền bảng hyperparameter đúng theo lần chạy cuối.
- [ ] Điền bảng so sánh ba mô hình.
- [ ] Thêm classification report theo từng lớp.
- [ ] Thêm confusion matrix.
- [ ] Thêm train loss và validation loss.
- [ ] Thêm ít nhất năm ví dụ error analysis.
- [ ] Chèn screenshot dashboard.
- [ ] Cập nhật phần kết luận bằng số liệu thực tế.

## Kiểm tra tính trung thực kỹ thuật

- [ ] Không nói đã dùng semantic search nếu chưa triển khai.
- [ ] Không nói đã dùng vector database nếu chưa tích hợp.
- [ ] Không nói mô hình đạt metric cụ thể nếu chưa chạy test set.
- [ ] Không dùng Accuracy làm metric duy nhất khi dữ liệu lệch lớp.
- [ ] Không để cùng repository xuất hiện trong train và test.
- [ ] Không gọi rule-based classifier là mô hình Deep Learning.

---

# PHỤ LỤC B. DANH SÁCH HÌNH ĐỀ XUẤT

| Hình | Nội dung | Công cụ có thể dùng |
|---|---|---|
| Hình 1 | Transformer Encoder hoặc attention overview | Canva, draw.io |
| Hình 2 | Phân bố dữ liệu theo nhãn | Python matplotlib |
| Hình 3 | Kiến trúc classifier đề xuất | draw.io |
| Hình 4 | Confusion matrix | sklearn + seaborn |
| Hình 5 | Train loss và validation loss | matplotlib |
| Hình 6 | Validation Macro-F1 theo epoch | matplotlib |
| Hình 7 | Kiến trúc tổng thể hệ thống | draw.io |
| Hình 8 | Dashboard ứng dụng | Screenshot |

---

# PHỤ LỤC C. DÀN Ý SLIDE THUYẾT TRÌNH 12-15 PHÚT

| Slide | Nội dung | Thời lượng |
|---|---|---:|
| 1 | Tên đề tài và thành viên | 30 giây |
| 2 | Bài toán: GitHub AI repos tăng nhanh, khó phân loại | 1 phút |
| 3 | Hạn chế của keyword rule-based | 1 phút |
| 4 | Dataset và sáu nhãn | 1 phút |
| 5 | Transformer và fine-tuning | 2 phút |
| 6 | Ba mô hình so sánh | 1 phút |
| 7 | Kiến trúc Transformer classifier | 1 phút |
| 8 | Kết quả tổng quan | 1 phút |
| 9 | Confusion matrix và error analysis | 1.5 phút |
| 10 | Tích hợp vào GitHub AI Trend Analyzer | 1.5 phút |
| 11 | Demo dashboard hoặc API inference | 2 phút |
| 12 | Kết luận và hướng phát triển | 1 phút |

---

# PHỤ LỤC D. PHẦN CÓ THỂ LƯỢC BỎ NẾU BÁO CÁO BỊ GIỚI HẠN SỐ TRANG

Nếu báo cáo chỉ được phép dài khoảng 15-20 trang, ưu tiên giữ:

1. Tóm tắt.
2. Giới thiệu.
3. Cơ sở Transformer ở mức vừa đủ.
4. Dataset và gán nhãn.
5. Ba mô hình so sánh.
6. Thực nghiệm, confusion matrix và error analysis.
7. Tích hợp hệ thống ở mức 1-2 trang.
8. Kết luận.

Có thể rút ngắn:

- Phần mô tả chi tiết hạ tầng Kafka, Spark và ClickHouse.
- API request/response mẫu.
- Danh sách đầy đủ hướng phát triển.
- Một phần công thức cơ bản nếu giảng viên ưu tiên thực nghiệm.

