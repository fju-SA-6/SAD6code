<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>畢業學分查核結果</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</head>
<body class="bg-light">
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card shadow">
                    <div class="card-header bg-success text-white">
                        <h1 class="card-title mb-0">畢業學分查核結果</h1>
                    </div>
                    <div class="card-body">
                        <?php
                        include 'config.php';

                        // Graduation requirements (adjust as needed)
                        $total_required = 128;
                        $required_required = 80;
                        $elective_required = 48;

                        $selected_courses = isset($_POST['courses']) ? $_POST['courses'] : [];

                        $total_credits = 0;
                        $required_credits = 0;
                        $elective_credits = 0;

                        if (!empty($selected_courses)) {
                            $ids = implode(',', array_map('intval', $selected_courses));
                            $sql = "SELECT course_name, credits, category FROM FJU_Courses WHERE id IN ($ids)";
                            $result = $conn->query($sql);

                            if ($result->num_rows > 0) {
                                echo "<h3 class='mb-3'>已修習課程：</h3>";
                                echo "<ul class='list-group mb-4'>";
                                while($row = $result->fetch_assoc()) {
                                    $badgeClass = $row['category'] == '必修' ? 'bg-danger' : 'bg-success';
                                    echo "<li class='list-group-item d-flex justify-content-between align-items-center'>";
                                    echo htmlspecialchars($row['course_name']);
                                    echo "<span><span class='badge $badgeClass me-2'>" . $row['category'] . "</span><small class='text-muted'>(" . $row['credits'] . " 學分)</small></span>";
                                    echo "</li>";
                                    $total_credits += $row['credits'];
                                    if ($row['category'] == '必修') {
                                        $required_credits += $row['credits'];
                                    } else {
                                        $elective_credits += $row['credits'];
                                    }
                                }
                                echo "</ul>";
                            }
                        } else {
                            echo "<div class='alert alert-warning'>您沒有勾選任何課程。</div>";
                        }

                        // Credits summary
                        echo "<h3 class='mb-3'>學分統計：</h3>";
                        echo "<div class='row mb-4'>";
                        echo "<div class='col-md-4'><div class='card text-center'><div class='card-body'><h5 class='card-title'>總學分</h5><p class='card-text display-6'>$total_credits / $total_required</p></div></div></div>";
                        echo "<div class='col-md-4'><div class='card text-center'><div class='card-body'><h5 class='card-title'>必修學分</h5><p class='card-text display-6'>$required_credits / $required_required</p></div></div></div>";
                        echo "<div class='col-md-4'><div class='card text-center'><div class='card-body'><h5 class='card-title'>選修學分</h5><p class='card-text display-6'>$elective_credits / $elective_required</p></div></div></div>";
                        echo "</div>";

                        $total_remaining = max(0, $total_required - $total_credits);
                        $required_remaining = max(0, $required_required - $required_credits);
                        $elective_remaining = max(0, $elective_required - $elective_credits);

                        $alertClass = ($total_remaining == 0 && $required_remaining == 0 && $elective_remaining == 0) ? 'alert-success' : 'alert-danger';
                        $statusText = ($total_remaining == 0 && $required_remaining == 0 && $elective_remaining == 0) ? '恭喜！您已滿足畢業要求。' : '您尚未滿足畢業要求。';

                        echo "<div class='alert $alertClass mt-4'>";
                        echo "<h4>畢業狀態：</h4>";
                        echo "<p>$statusText</p>";
                        if ($total_remaining > 0 || $required_remaining > 0 || $elective_remaining > 0) {
                            echo "<p>還需修習：</p>";
                            echo "<ul>";
                            if ($required_remaining > 0) echo "<li>必修學分：$required_remaining</li>";
                            if ($elective_remaining > 0) echo "<li>選修學分：$elective_remaining</li>";
                            echo "</ul>";
                            
                            // 推薦課程區塊
                            $not_taken_condition = "";
                            if (!empty($selected_courses)) {
                                $ids = implode(',', array_map('intval', $selected_courses));
                                $sql_taken_names = "SELECT course_name FROM FJU_Courses WHERE id IN ($ids)";
                                $result_taken_names = $conn->query($sql_taken_names);
                                $taken_names = [];
                                if ($result_taken_names && $result_taken_names->num_rows > 0) {
                                    while($tn = $result_taken_names->fetch_assoc()) {
                                        $taken_names[] = "'" . $conn->real_escape_string($tn['course_name']) . "'";
                                    }
                                }
                                if (!empty($taken_names)) {
                                    $not_taken_name_str = implode(',', $taken_names);
                                    $not_taken_condition = "AND course_name NOT IN ($not_taken_name_str)";
                                }
                            }

                            // --- 整合 test2.py 的畢業檢核缺口 ---
                            $priority_cases = [];
                            $sql_missing_req = "SELECT requirement_name FROM FJU_Graduation_Check WHERE grade = '尚未修課'";
                            $res_missing_req = $conn->query($sql_missing_req);
                            if ($res_missing_req && $res_missing_req->num_rows > 0) {
                                while($row = $res_missing_req->fetch_assoc()) {
                                    $req_name = $row['requirement_name'];
                                    $req_name_clean = str_replace(['通識領域', '領域'], '', $req_name);
                                    if (strpos($req_name_clean, '-') !== false) {
                                        $parts = explode('-', $req_name_clean);
                                        $req_name_clean = end($parts);
                                    }
                                    if (!empty($req_name_clean)) {
                                        $safe_name = $conn->real_escape_string($req_name_clean);
                                        $priority_cases[] = "course_name LIKE '%$safe_name%'";
                                    }
                                }
                            }
                            
                            $order_by_clause = "RAND()";
                            if (!empty($priority_cases)) {
                                $priority_sql = implode(' OR ', $priority_cases);
                                $order_by_clause = "($priority_sql) DESC, RAND()";
                            }
                            // ----------------------------------------

                            echo "<hr class='my-4 border-secondary'>";
                            echo "<h5>💡 推薦修課清單 (優先推薦檢核表缺口，並根據缺少學分動態補齊)：</h5>";
                            echo "<div class='row mt-3'>";
                            
                            if ($required_remaining > 0) {
                                echo "<div class='col-md-6'>";
                                echo "<h6 class='text-danger fw-bold'>【必修】還缺 $required_remaining 學分</h6>";
                                $sql_req = "SELECT course_name, credits FROM FJU_Courses WHERE category = '必修' AND credits > 0 $not_taken_condition GROUP BY course_name ORDER BY $order_by_clause LIMIT 50";
                                $res_req = $conn->query($sql_req);
                                if ($res_req && $res_req->num_rows > 0) {
                                    echo "<ul class='list-group mb-3 shadow-sm'>";
                                    $accumulated = 0;
                                    while($r = $res_req->fetch_assoc()) {
                                        echo "<li class='list-group-item d-flex justify-content-between align-items-center bg-white'>";
                                        echo htmlspecialchars($r['course_name']);
                                        echo "<span class='badge bg-danger rounded-pill'>" . $r['credits'] . " 學分</span>";
                                        echo "</li>";
                                        
                                        $accumulated += $r['credits'];
                                        if ($accumulated >= $required_remaining) {
                                            break;
                                        }
                                    }
                                    echo "</ul>";
                                    echo "<small class='text-muted d-block mb-3'>※ 推薦以上課程，合計 <strong>$accumulated</strong> 學分可滿足必修要求。</small>";
                                } else {
                                    echo "<p class='text-muted small'>暫無足夠的必修課程資料可推薦。</p>";
                                }
                                echo "</div>";
                            }

                            if ($elective_remaining > 0) {
                                echo "<div class='col-md-6'>";
                                echo "<h6 class='text-success fw-bold'>【選修】還缺 $elective_remaining 學分</h6>";
                                $sql_opt = "SELECT course_name, credits FROM FJU_Courses WHERE category = '選修' AND credits > 0 $not_taken_condition GROUP BY course_name ORDER BY $order_by_clause LIMIT 100";
                                $res_opt = $conn->query($sql_opt);
                                if ($res_opt && $res_opt->num_rows > 0) {
                                    echo "<ul class='list-group mb-3 shadow-sm'>";
                                    $accumulated = 0;
                                    while($r = $res_opt->fetch_assoc()) {
                                        echo "<li class='list-group-item d-flex justify-content-between align-items-center bg-white'>";
                                        echo htmlspecialchars($r['course_name']);
                                        echo "<span class='badge bg-success rounded-pill'>" . $r['credits'] . " 學分</span>";
                                        echo "</li>";
                                        
                                        $accumulated += $r['credits'];
                                        if ($accumulated >= $elective_remaining) {
                                            break;
                                        }
                                    }
                                    echo "</ul>";
                                    echo "<small class='text-muted d-block mb-3'>※ 推薦以上課程，合計 <strong>$accumulated</strong> 學分可滿足選修要求。</small>";
                                } else {
                                    echo "<p class='text-muted small'>暫無足夠的選修課程資料可推薦。</p>";
                                }
                                echo "</div>";
                            }
                            
                            echo "</div>"; // end row
                        }
                        echo "</div>";

                        $conn->close();
                        ?>
                        <div class="mt-4">
                            <a href="index.php" class="btn btn-primary">返回重新查核</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>