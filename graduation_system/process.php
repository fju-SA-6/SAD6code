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