[1mdiff --git a/new_uaiss.html b/new_uaiss.html[m
[1mindex 6b943f1..fc08a7d 100644[m
[1m--- a/new_uaiss.html[m
[1m+++ b/new_uaiss.html[m
[36m@@ -74,7 +74,7 @@[m
         .exam-type-btn { background: var(--bg-surface); border: 2px solid var(--border); border-radius: 12px; padding: 16px; text-align: center; cursor: pointer; }[m
         .exam-type-btn.selected { border-color: var(--accent); background: rgba(59, 130, 246, 0.1); }[m
         .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: flex-end; z-index: 200; }[m
[31m-        .modal-content { background: var(--bg-surface); border-radius: 24px 24px 0 0; padding: 24px; max-height: 80vh; overflow-y: auto; width: 100%; animation: slideUp 0.3s ease; }[m
[32m+[m[32m        .modal-content { background: var(--bg-surface); border-radius: 24px 24px 24px 24px; padding: 24px; max-height: 80vh; overflow-y: auto; width: 100%; animation: slideUp 0.3s ease; }[m
         @keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }[m
         .empty-state { text-align: center; padding: 48px 20px; color: var(--text-secondary); }[m
         .toast { position: fixed; bottom: 90px; left: 20px; right: 20px; background: var(--bg-surface); color: var(--text-primary); padding: 12px 16px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 150; animation: slideUp 0.3s ease; text-align: center; }[m
[36m@@ -96,9 +96,6 @@[m
         .profile-role { font-size: 12px; padding: 4px 12px; border-radius: 20px; display: inline-block; margin-top: 8px; }[m
         .role-admin { background: linear-gradient(135deg, #8B5CF6, #6366F1); color: white; }[m
         .role-employee { background: var(--bg-primary); color: var(--text-secondary); border: 1px solid var(--border); }[m
[31m-        .form-group { margin-bottom: 20px; }[m
[31m-        .form-group label { display: block; margin-bottom: 8px; font-weight: 500; font-size: 14px; }[m
[31m-        .form-group input { width: 100%; padding: 12px 16px; border: 1px solid var(--border); border-radius: 12px; background: var(--bg-primary); color: var(--text-primary); font-family: inherit; font-size: 14px; }[m
         .btn-save { width: 100%; padding: 12px; background: var(--accent); color: white; border: none; border-radius: 12px; font-weight: 600; cursor: pointer; }[m
         .profile-actions { margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--border); text-align: center; }[m
         .btn-logout { background: none; border: none; color: var(--danger); cursor: pointer; font-size: 14px; padding: 8px; }[m
[36m@@ -106,11 +103,12 @@[m
         .sick-color { color: var(--sick); }[m
         .trip-color { color: var(--business-trip); }[m
         .vacation-color { color: var(--vacation); }[m
[31m-        /* Дополнительные стили для красной индикации */[m
[31m-        .expiring-critical {border-left: 4px solid var(--danger) !important;[m
[31m-        background: rgba(239, 68, 68, 0.05) !important;}[m
[31m-        .text-critical { color: var(--danger) !important;font-weight: bold !important;}[m
[32m+[m[32m        .expiring-critical { border-left: 4px solid var(--danger) !important; background: rgba(239, 68, 68, 0.05) !important; }[m
[32m+[m[32m        .text-critical { color: var(--danger) !important; font-weight: bold !important; }[m
         .loading { text-align: center; padding: 40px; color: var(--text-secondary); }[m
[32m+[m[32m        .sort-buttons { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }[m
[32m+[m[32m        .sort-btn { background: var(--bg-primary); border: 1px solid var(--border); border-radius: 20px; padding: 6px 12px; font-size: 12px; cursor: pointer; transition: all 0.2s; }[m
[32m+[m[32m        .sort-btn.active { background: var(--accent); color: white; border-color: var(--accent); }[m
     </style>[m
 </head>[m
 <body>[m
[36m@@ -131,12 +129,14 @@[m
         let myStatuses = [];[m
         let examTypes = [];[m
         let statusStats = null;[m
[31m-        let expiringExams = [];[m
         let isLoading = false;[m
[31m-        let newPassword = '';[m
[31m-        let confirmPassword = '';[m
[31m-        let passwordError = '';[m
[31m-        let emailError = '';[m
[32m+[m[32m        let examSortType = 'date_asc';[m
[32m+[m[41m        [m
[32m+[m[32m        let editingExamId = null;[m
[32m+[m[32m        let editingExamName = null;[m
[32m+[m[32m        let editingExamDate = null;[m
[32m+[m[41m        [m
[32m+[m[32m        let deleteCallback = null;[m
 [m
         function setDarkMode(enabled) {[m
             isDarkMode = enabled;[m
[36m@@ -202,8 +202,6 @@[m
                 if (statusRes.ok) myStatuses = await statusRes.json();[m
                 const statsRes = await apiRequest('/status/current');[m
                 if (statsRes.ok) statusStats = await statsRes.json();[m
[31m-                const expiringRes = await apiRequest('/exams/expiring');[m
[31m-                if (expiringRes.ok) expiringExams = await expiringRes.json();[m
                 const meRes = await apiRequest('/auth/me');[m
                 if (meRes.ok) {[m
                     const meData = await meRes.json();[m
[36m@@ -261,27 +259,6 @@[m
             }[m
         }[m
 [m
[31m-        async function closeSickLeave(statusId) {[m
[31m-            try {[m
[31m-                const response = await apiRequest(`/status/${statusId}/close`, {[m
[31m-                    method: 'PATCH'[m
[31m-                });[m
[31m-                if (response.ok) {[m
[31m-                    showToast('✅ Больничный закрыт');[m
[31m-                    await loadAllData();[m
[31m-                    render();[m
[31m-                    return true;[m
[31m-                } else {[m
[31m-                    const error = await response.json();[m
[31m-                    showToast(`❌ ${error.detail || 'Ошибка закрытия'}`);[m
[31m-                    return false;[m
[31m-                }[m
[31m-            } catch (error) {[m
[31m-                showToast('❌ Ошибка соединения');[m
[31m-                return false;[m
[31m-            }[m
[31m-        }[m
[31m-[m
         function logout() {[m
             authToken = null;[m
             localStorage.removeItem('authToken');[m
[36m@@ -297,14 +274,482 @@[m
             render();[m
         }[m
 [m
[31m-        function getCurrentExams() { return myExams; }[m
[31m-        function getCurrentStatusHistory() { return myStatuses; }[m
[31m-        [m
         function getActiveStatus() {[m
[31m-            return myStatuses.find(s => s.is_active === true);[m
[32m+[m[32m            const today = new Date();[m
[32m+[m[32m            today.setHours(0, 0, 0, 0);[m
[32m+[m[41m            [m
[32m+[m[32m            return myStatuses.find(s => {[m
[32m+[m[32m                if (!s.is_active) return false;[m
[32m+[m[41m                [m
[32m+[m[32m                if (s.start_date) {[m
[32m+[m[32m                    const startParts = s.start_date.split('.');[m
[32m+[m[32m                    const startDate = new Date(startParts[2], startParts[1] - 1, startParts[0]);[m
[32m+[m[32m                    if (startDate > today) {[m
[32m+[m[32m                        return false;[m
[32m+[m[32m                    }[m
[32m+[m[32m                }[m
[32m+[m[32m                return true;[m
[32m+[m[32m            });[m
[32m+[m[32m        }[m
[32m+[m[41m        [m
[32m+[m[32m        function getExamTypeEmoji(typeName) {[m[41m [m
[32m+[m[32m            const examType = examTypes.find(t => t.name === typeName);[m[41m [m
[32m+[m[32m            return examType?.emoji || '📚';[m[41m [m
         }[m
         [m
[31m-        function getExamTypeEmoji(typeName) { const examType = examTypes.find(t => t.name === typeName); return examType?.emoji || '📚'; }[m
[32m+[m[32m        function getSortedExams() {[m
[32m+[m[32m            const exams = [...myExams];[m
[32m+[m[41m            [m
[32m+[m[32m            switch(examSortType) {[m
[32m+[m[32m                case 'date_asc':[m
[32m+[m[32m                    return exams.sort((a, b) => {[m
[32m+[m[32m                        const dateA = a.date.split('.').reverse().join('-');[m
[32m+[m[32m                        const dateB = b.date.split('.').reverse().join('-');[m
[32m+[m[32m                        return dateA.localeCompare(dateB);[m
[32m+[m[32m                    });[m
[32m+[m[32m                case 'date_desc':[m
[32m+[m[32m                    return exams.sort((a, b) => {[m
[32m+[m[32m                        const dateA = a.date.split('.').reverse().join('-');[m
[32m+[m[32m                        const dateB = b.date.split('.').reverse().join('-');[m
[32m+[m[32m                        return dateB.localeCompare(dateA);[m
[32m+[m[32m                    });[m
[32m+[m[32m                case 'days_left_asc':[m
[32m+[m[32m                    return exams.sort((a, b) => a.days_left - b.days_left);[m
[32m+[m[32m                default:[m
[32m+[m[32m                    return exams;[m
[32m+[m[32m            }[m
[32m+[m[32m        }[m
[32m+[m[41m        [m
[32m+[m[32m        window.setExamSort = (type) => {[m
[32m+[m[32m            examSortType = type;[m
[32m+[m[32m            render();[m
[32m+[m[32m        };[m
[32m+[m
[32m+[m[32m        window.showConfirmModal = (title, message, onConfirm) => {[m
[32m+[m[32m            deleteCallback = onConfirm;[m
[32m+[m[41m            [m
[32m+[m[32m            const modalHtml = `[m
[32m+[m[32m                <div class="modal-overlay" onclick="window.closeConfirmModal()">[m
[32m+[m[32m                    <div class="modal-content" onclick="event.stopPropagation()" style="max-width: 400px; margin: 0 auto; border-radius: 24px;">[m
[32m+[m[32m                        <div class="card-header" style="margin-bottom: 16px;">[m
[32m+[m[32m                            <div class="card-title">${title}</div>[m
[32m+[m[32m                            <button class="btn btn-outline" onclick="window.closeConfirmModal()" style="padding: 4px 8px; border-radius: 40px;">✕</button>[m
[32m+[m[32m                        </div>[m
[32m+[m[32m                        <div style="text-align: center; margin-bottom: 20px;">[m
[32m+[m[32m                            <div style="font-size: 48px; margin-bottom: 12px;">🗑️</div>[m
[32m+[m[32m                            <div style="font-size: 16px; margin-bottom: 8px;">${message}</div>[m
[32m+[m[32m                            <div style="font-size: 13px; color: var(--text-secondary);">Это действие нельзя отменить</div>[m
[32m+[m[32m                        </div>[m
[32m+[m[32m                        <div style="display: flex; gap: 12px; margin-top: 20px;">[m
[32m+[m[32m                            <button class="btn btn-primary" style="flex: 1; background: var(--danger);" onclick="window.confirmDelete()">[m
[32m+[m[32m                                🗑️ Удалить[m
[32m+[m[32m                            </button>[m
[32m+[m[32m                            <button class="btn btn-outline" style="flex: 1;" onclick="window.closeConfirmModal()">[m
[32m+[m[32m                                Отмена[m
[32m+[m[32m                            </button>[m
[32m+[m[32m                        </div>[m
[32m+[m[32m                    </div>[m
[32m+[m[32m                </div>[m
[32m+[m[32m            `;[m
[32m+[m[41m            [m
[32m+[m[32m            const existingModal = document.getElementById('confirmModal');[m
[32m+[m[32m            if (existingModal) existingModal.remove();[m
[32m+[m[41m            [m
[32m+[m[32m            const modalDiv = document.createElement('div');[m
[32m+[m[32m            modalDiv.id = 'confirmModal';[m
[32m+[m[32m            modalDiv.innerHTML = modalHtml;[m
[32m+[m[32m            document.body.appendChild(modalDiv);[m
[32m+[m[32m        };[m
[32m+[m
[32m+[m[32m        window.closeConfirmModal = () => {[m
[32m+[m[32m            const modal = document.getElementById('confirmModal');[m
[32m+[m[32m            if (modal) modal.remove();[m
[32m+[m[32m            deleteCallback = null;[m
[32m+[m[32m        };[m
[32m+[m
[32m+[m[32m        window.confirmDelete = () => {[m
[32m+[m[32m            if (deleteCallback) {[m
[32m+[m[32m                deleteCallback();[m
[32m+[m[32m            }[m
[32m+[m[32m            window.closeConfirmModal();[m
[32m+[m[32m        };[m
[32m+[m
[32m+[m[32m        window.openEditExamModal = (examId, examName, currentDate) => {[m
[32m+[m[32m            editingExamId = examId;[m
[32m+[m[32m            editingExamName = examName;[m
[32m+[m[32m            editingExamDate = currentDate;[m
[32m+[m[41m            [m
[32m+[m[32m            let formattedDate = '';[m
[32m+[m[32m            if (currentDate) {[m
[32m+[m[32m                const parts = currentDate.split('.');[m
[32m+[m[32m                if (parts.length === 3) {[m
[32m+[m[32m                    formattedDate = `${parts[2]}-${parts[1]}-${parts[0]}`;[m
[32m+[m[32m                }[m
[32m+[m[32m            }[m
[32m+[m[41m            [m
[32m+[m[32m            const modalHtml = `[m
[32m+[m[32m                <div class="modal-overlay" onclick="window.closeEditExamModal()">[m
[32m+[m[32m                    <div class="modal-content" onclick="event.stopPropagation()" style="max-width: 400px; margin: 0 auto; border-radius: 24px;">[m
[32m+[m[32m                        <div class="card-header" style="margin-bottom: 16px;">[m
[32m+[m[32m                            <div class="card-title">✏️ Редактировать экзамен</div>[m
[32m+[m[32m                            <button class="btn btn-outline" onclick="window.closeEditExamModal()" style="padding: 4px 8px; border-radius: 40px;">✕</button>[m
[32m+[m[32m                        </div>[m
[32m+[m[32m                        <div class="form-group">[m
[32m+[m[32m                            <label class="form-label">📚 Тип экзамена</label>[m
[32m+[m[32m                            <input type="text" class="form-input" value="${editingExamName}" disabled style="background: var(--bg-primary); opacity: 0.7;">[m
[32m+[m[32m                        </div>[m
[32m+[m[32m                        <div class="form-group">[m
[32m+[m[32m                            <label class="form-label">📅 Дата сдачи</label>[m
[32m+[m[32m                            <input type="date" class="form-input" id="editExamDate" value="${formattedDate}" max="${new Date().toISOString().split('T')[0]}">[m
[32m+[m[32m                            <small style="font-size: 11px; color: var(--text-secondary);">Нельзя выбрать дату из будущего</small>[m
[32m+[m[32m                        </div>[m
[32m+[m[32m                        <div style="display: flex; gap: 12px; margin-top: 20px;">[m
[32m+[m[32m                            <button class="btn btn-primary" style="flex: 1;" onclick="window.saveEditedExamDate()">[m
[32m+[m[32m                                💾 Сохранить[m
[32m+[m[32m                            </button>[m
[32m+[m[32m                            <button class="btn btn-outline" style="flex: 1;" onclick="window.closeEditExamModal()">[m
[32m+[m[32m                                Отмена[m
[32m+[m[32m                            </button>[m
[32m+[m[32m                        </div>[m
[32m+[m[32m                    </div>[m
[32m+[m[32m                </div>[m
[32m+[m[32m            `;[m
[32m+[m[41m            [m
[32m+[m[32m            const existingModal = document.getElementById('editExamModal');[m
[32m+[m[32m            if (existingModal) existingModal.remove();[m
[32m+[m[41m            [m
[32m+[m[32m            const modalDiv = document.createElement('div');[m
[32m+[m[32m            modalDiv.id = 'editExamModal';[m
[32m+[m[32m            modalDiv.innerHTML = modalHtml;[m
[32m+[m[32m            document.body.appendChild(modalDiv);[m
[32m+[m[32m        };[m
[32m+[m
[32m+[m[32m        window.closeEditExamModal = () => {[m
[32m+[m[32m            const modal = document.getElementById('editExamModal');[m
[32m+[m[32m            if (modal) modal.remove();[m
[32m+[m[32m            editingExamId = null;[m
[32m+[m[32m            editingExamName = null;[m
[32m+[m[32m            editingExamDate = null;[m
[32m+[m[32m        };[m
[32m+[m
[32m+[m[32m        window.saveEditedExamDate = async () => {[m
[32m+[m[32m            const dateInput = document.getElementById('editExamDate');[m
[32m+[m[41m            [m
[32m+[m[32m            if (!dateInput || !dateInput.value) {[m
[32m+[m[32m                showToast('❌ Выберите дату');[m
[32m+[m[32m                return;[m
[32m+[m[32m            }[m
[32m+[m[41m            [m
[32m+[m[32m            const newDate = dateInput.value.split('-').reverse().join('.');[m
[32m+[m[41m            [m
[32m+[m[32m            const selectedDate = new Date(dateInput.value);[m
[32m+[m[32m            if (selectedDate > new Date()) {[m
[32m+[m[32m                showToast('❌ Нельзя выбрать дату из будущего');[m
[32m+[m[32m                return;[m
[32m+[m[32m            }[m
[32m+[m[41m            [m
[32m+[m[32m            try {[m
[32m+[m[32m                const response = await apiRequest(`/exams/${editingExamId}`, {[m
[32m+[m[32m                    method: 'PUT',[m
[32m+[m[32m                    body: JSON.stringify({ date: newDate })[m
[32m+[m[32m                });[m
[32m+[m[41m                [m
[32m+[m[32m                if (response.ok) {[m
[32m+[m[32m                    showToast('✅ Дата экзамена обновлена');[m
[32m+[m[32m                    window.closeEditExamModal();[m
[32m+[m[32m                    await loadAllData();[m
[32m+[m[32m                    render();[m
[32m+[m[32m                } else {[m
[32m+[m[32m                    const error = await response.json();[m
[32m+[m[32m                    showToast(`❌ ${error.detail || 'Ошибка обновления'}`);[m
[32m+[m[32m                }[m
[32m+[m[32m            } catch (error) {[m
[32m+[m[32m                console.error('Ошибка:', error);[m
[32m+[m[32m                showToast('❌ Ошибка соединения');[m
[32m+[m[32m            }[m
[32m+[m[32m        };[m
[32m+[m
[32m+[m[32m        window.editStatusDates = (statusId, statusText, startDate, endDate) => {[m
[32m+[m[32m            let title = '✏️ Редактировать даты';[m
[32m+[m[32m            if (statusText.includes('Командировка')) title = '✈️ Редактировать командировку';[m
[32m+[m[32m            else if (statusText.includes('Отпуск')) title = '🏖️ Редактировать отпуск';[m
[32m+[m[32m            else if (statusText.includes('Больничный')) title = '🤒 Редактировать больничный';[m
[32m+[m[41m            [m
[32m+[m[32m            const startDateFormatted = startDate ? startDate.split('.').reverse().join('-') : '';[m
[32m+[m[32m            let endDateFormatted = '';[m
[32m+[m[32m            if (endDate && endDate !== '') {[m
[32m+[m[32m                endDateFormatted = endDate.split('.').reverse().join('-');[m
[32m+[m[32m            }[m
[32m+[m[41m            [m
[32m+[m[32m            const modalHtml = `[m
[32m+[m[32m                <div class="modal-overlay" onclick="window.closeEditStatusModal()">[m
[32m+[m[32m                    <div class="