<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>畢業學分查核系統</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <style>
        .course-card { margin-bottom: 10px; }
        .required { border-left: 5px solid #dc3545; }
        .elective { border-left: 5px solid #28a745; }
    </style>
</head>
<body class="bg-light">
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card shadow">
                    <div class="card-header bg-primary text-white">
                        <h1 class="card-title mb-0">畢業學分查核系統</h1>
                    </div>
                    <div class="card-body">
                        <p class="lead">請勾選您已修習的課程：</p>
                        <div class="mb-3">
                            <input type="text" id="searchInput" class="form-control" placeholder="搜尋課程名稱...">
                        </div>
                        <form action="process.php" method="post" id="courseForm">
                            <div id="courseList">
                                <?php
                                include 'config.php';

                                // Fetch courses
                                $sql = "SELECT id, course_name, credits, category FROM FJU_Courses GROUP BY course_name ORDER BY category, course_name";
                                $result = $conn->query($sql);

                                if ($result->num_rows > 0) {
                                    while($row = $result->fetch_assoc()) {
                                        $class = $row['category'] == '必修' ? 'required' : 'elective';
                                        $badgeClass = $row['category'] == '必修' ? 'bg-danger' : 'bg-success';
                                        echo "<div class='course-card $class' data-name='" . htmlspecialchars($row['course_name']) . "'>";
                                        echo "<div class='form-check'>";
                                        echo "<input class='form-check-input' type='checkbox' name='courses[]' value='" . $row['id'] . "' id='course" . $row['id'] . "'>";
                                        echo "<label class='form-check-label' for='course" . $row['id'] . "'>";
                                        echo "<strong>" . htmlspecialchars($row['course_name']) . "</strong> ";
                                        echo "<span class='badge $badgeClass'>" . $row['category'] . "</span> ";
                                        echo "<small class='text-muted'>(" . $row['credits'] . " 學分)</small>";
                                        echo "</label>";
                                        echo "</div>";
                                        echo "</div>";
                                    }
                                } else {
                                    echo "<p class='text-muted'>沒有課程資料。</p>";
                                }

                                $conn->close();
                                ?>
                            </div>
                            <div class="mt-4">
                                <button type="submit" class="btn btn-primary btn-lg">查核學分</button>
                                <button type="button" class="btn btn-secondary btn-lg ms-2" onclick="selectAll()">全選</button>
                                <button type="button" class="btn btn-outline-secondary btn-lg ms-2" onclick="clearAll()">清除</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Search functionality
        document.getElementById('searchInput').addEventListener('input', function() {
            const filter = this.value.toLowerCase();
            const courses = document.querySelectorAll('.course-card');
            courses.forEach(course => {
                const name = course.getAttribute('data-name').toLowerCase();
                if (name.includes(filter)) {
                    course.style.display = '';
                } else {
                    course.style.display = 'none';
                }
            });
        });

        // Select all courses
        function selectAll() {
            const checkboxes = document.querySelectorAll('input[name="courses[]"]');
            checkboxes.forEach(cb => cb.checked = true);
        }

        // Clear all selections
        function clearAll() {
            const checkboxes = document.querySelectorAll('input[name="courses[]"]');
            checkboxes.forEach(cb => cb.checked = false);
        }
    </script>
</body>
</html>