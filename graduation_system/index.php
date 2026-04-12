<!DOCTYPE html>
<html lang="zh-TW">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>畢業學分查核系統</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <style>
        .course-card {
            margin-bottom: 10px;
        }

        .required {
            border-left: 5px solid #dc3545;
        }

        .elective {
            border-left: 5px solid #28a745;
        }
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
                        <div class="row mb-3">
                            <div class="col-md-4">
                                <input type="text" id="searchInput" class="form-control" placeholder="搜尋課程名稱...">
                            </div>
                            <div class="col-md-3">
                                <select id="semesterFilter" class="form-select">
                                    <option value="">所有學期</option>
                                    <option value="上學期">上學期</option>
                                    <option value="下學期">下學期</option>
                                </select>
                            </div>
                            <div class="col-md-3">
                                <select id="dayFilter" class="form-select">
                                    <option value="">所有星期</option>
                                    <option value="星期一">星期一</option>
                                    <option value="星期二">星期二</option>
                                    <option value="星期三">星期三</option>
                                    <option value="星期四">星期四</option>
                                    <option value="星期五">星期五</option>
                                    <option value="星期六">星期六</option>
                                    <option value="星期日">星期日</option>
                                </select>
                            </div>
                            <div class="col-md-2">
                                <select id="itemsPerPage" class="form-select">
                                    <option value="100" selected>100 筆 / 頁</option>
                                    <option value="200">200 筆 / 頁</option>
                                    <option value="300">300 筆 / 頁</option>
                                    <option value="all">全部顯示</option>
                                </select>
                            </div>
                        </div>
                        <form action="process.php" method="post" id="courseForm">
                            <div id="courseList">
                                <?php
                                include 'config.php';

                                // 取得已過關的個人成績課程名稱
                                $passed_courses = [];
                                $sql_passed = "SELECT course_name, grade FROM FJU_Personal_Grades";
                                $result_passed = $conn->query($sql_passed);
                                if ($result_passed && $result_passed->num_rows > 0) {
                                    while ($rp = $result_passed->fetch_assoc()) {
                                        $grade = trim($rp['grade']);
                                        $is_passed = false;
                                        // 判斷是否及格或抵免
                                        if (is_numeric($grade)) {
                                            if ($grade >= 60) {
                                                $is_passed = true;
                                            }
                                        } else {
                                            // 非數字成績，例如：抵免、通過、A, B, C 等（排除不及格與停修）
                                            if (!in_array($grade, ['不及格', '未通過', '停修', 'W', 'F'])) {
                                                $is_passed = true;
                                            }
                                        }

                                        if ($is_passed) {
                                            $passed_courses[] = $rp['course_name'];
                                        }
                                    }
                                }

                                // Fetch courses
                                $sql = "SELECT id, course_name, credits, category, GROUP_CONCAT(DISTINCT semester) as semesters, GROUP_CONCAT(DISTINCT day_of_week) as days, GROUP_CONCAT(DISTINCT teacher SEPARATOR ', ') as teachers FROM FJU_Courses GROUP BY course_name ORDER BY category, course_name";
                                $result = $conn->query($sql);

                                if ($result->num_rows > 0) {
                                    while ($row = $result->fetch_assoc()) {
                                        $class = $row['category'] == '必修' ? 'required' : 'elective';
                                        $badgeClass = $row['category'] == '必修' ? 'bg-danger' : 'bg-success';

                                        // 如果課程在 $passed_courses 陣列裡，表示已修過，將 checkbox 設為 checked
                                        $isChecked = in_array($row['course_name'], $passed_courses) ? 'checked' : '';

                                        echo "<div class='course-card $class' data-name='" . htmlspecialchars($row['course_name']) . "' data-semesters='" . htmlspecialchars($row['semesters'] ?? '') . "' data-days='" . htmlspecialchars($row['days'] ?? '') . "'>";
                                        echo "<div class='form-check'>";
                                        echo "<input class='form-check-input' type='checkbox' name='courses[]' value='" . $row['id'] . "' id='course" . $row['id'] . "' $isChecked>";
                                        echo "<label class='form-check-label' for='course" . $row['id'] . "'>";
                                        echo "<strong>" . htmlspecialchars($row['course_name']) . "</strong> ";
                                        echo "<span class='badge $badgeClass'>" . $row['category'] . "</span> ";
                                        echo "<small class='text-muted'>(" . $row['credits'] . " 學分)</small>";
                                        $teachers = !empty($row['teachers']) ? htmlspecialchars($row['teachers']) : '無資料';
                                        echo "<small class='text-muted ms-2'>| 授課教師：$teachers</small>";
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
                            <!-- Pagination Controls -->
                            <div class="d-flex justify-content-center mt-3">
                                <nav aria-label="Page navigation">
                                    <ul class="pagination" id="paginationControls">
                                        <!-- Will be populated by JS -->
                                    </ul>
                                </nav>
                            </div>
                            <div class="mt-4">
                                <button type="submit" class="btn btn-primary btn-lg">查核學分</button>
                                <button type="button" class="btn btn-secondary btn-lg ms-2"
                                    onclick="selectAll()">全選</button>
                                <button type="button" class="btn btn-outline-secondary btn-lg ms-2"
                                    onclick="clearAll()">清除</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentPage = 1;
        let itemsPerPage = '100';
        let searchQuery = '';
        let semesterQuery = '';
        let dayQuery = '';
        
        function updateDisplay() {
            const courses = Array.from(document.querySelectorAll('.course-card'));
            
            // 1. Filter by search query, semester and day
            const filteredCourses = courses.filter(course => {
                const name = course.getAttribute('data-name').toLowerCase();
                const semesters = course.getAttribute('data-semesters');
                const days = course.getAttribute('data-days');
                
                const matchName = name.includes(searchQuery);
                const matchSemester = semesterQuery === '' || semesters.includes(semesterQuery);
                const matchDay = dayQuery === '' || days.includes(dayQuery);
                
                return matchName && matchSemester && matchDay;
            });
            
            // 2. Hide all courses first
            courses.forEach(course => course.style.display = 'none');
            
            // 3. Apply pagination
            let totalPages = 1;
            let displayCourses = [];
            
            if (itemsPerPage === 'all') {
                displayCourses = filteredCourses;
            } else {
                const limit = parseInt(itemsPerPage);
                totalPages = Math.ceil(filteredCourses.length / limit);
                if (currentPage > totalPages && totalPages > 0) currentPage = totalPages;
                
                const startIndex = (currentPage - 1) * limit;
                const endIndex = startIndex + limit;
                displayCourses = filteredCourses.slice(startIndex, endIndex);
            }
            
            // 4. Show the selected courses
            displayCourses.forEach(course => course.style.display = '');
            
            // 5. Render pagination controls
            renderPagination(totalPages);
        }
        
        function renderPagination(totalPages) {
            const paginationControls = document.getElementById('paginationControls');
            paginationControls.innerHTML = '';
            
            if (itemsPerPage === 'all' || totalPages <= 1) {
                return; // No pagination needed
            }
            
            // Prev button
            const prevLi = document.createElement('li');
            prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
            prevLi.innerHTML = `<a class="page-link" href="javascript:void(0)" onclick="goToPage(${currentPage - 1})">上一頁</a>`;
            paginationControls.appendChild(prevLi);
            
            // Page numbers
            for (let i = 1; i <= totalPages; i++) {
                if (totalPages > 15) {
                    if (i !== 1 && i !== totalPages && Math.abs(i - currentPage) > 2) {
                        if (Math.abs(i - currentPage) === 3) {
                            const ellipsisLi = document.createElement('li');
                            ellipsisLi.className = 'page-item disabled';
                            ellipsisLi.innerHTML = `<a class="page-link" href="javascript:void(0)">...</a>`;
                            paginationControls.appendChild(ellipsisLi);
                        }
                        continue;
                    }
                }
                
                const pageLi = document.createElement('li');
                pageLi.className = `page-item ${currentPage === i ? 'active' : ''}`;
                pageLi.innerHTML = `<a class="page-link" href="javascript:void(0)" onclick="goToPage(${i})">${i}</a>`;
                paginationControls.appendChild(pageLi);
            }
            
            // Next button
            const nextLi = document.createElement('li');
            nextLi.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
            nextLi.innerHTML = `<a class="page-link" href="javascript:void(0)" onclick="goToPage(${currentPage + 1})">下一頁</a>`;
            paginationControls.appendChild(nextLi);
        }
        
        function goToPage(page) {
            currentPage = page;
            updateDisplay();
        }

        // Search functionality
        document.getElementById('searchInput').addEventListener('input', function () {
            searchQuery = this.value.toLowerCase();
            currentPage = 1; // Reset to first page
            updateDisplay();
        });
        
        // Semester Filter change
        document.getElementById('semesterFilter').addEventListener('change', function () {
            semesterQuery = this.value;
            currentPage = 1; // Reset to first page
            updateDisplay();
        });
        
        // Day Filter change
        document.getElementById('dayFilter').addEventListener('change', function () {
            dayQuery = this.value;
            currentPage = 1; // Reset to first page
            updateDisplay();
        });
        
        // Items per page change
        document.getElementById('itemsPerPage').addEventListener('change', function () {
            itemsPerPage = this.value;
            currentPage = 1; // Reset to first page
            updateDisplay();
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
        
        // Initial setup on load
        document.addEventListener('DOMContentLoaded', () => {
            updateDisplay();
        });
    </script>
</body>

</html>