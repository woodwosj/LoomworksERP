/**
 * Loomworks Appointment - Portal Booking Interface
 * Handles date/time selection and booking submission
 */

(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        const appointmentApp = new AppointmentBookingApp();
        appointmentApp.init();
    });

    class AppointmentBookingApp {
        constructor() {
            this.calendarEl = document.getElementById('appointment-calendar');
            this.selectedDate = null;
            this.selectedTime = null;
            this.selectedResource = null;
            this.accessToken = null;
        }

        init() {
            if (!this.calendarEl) return;

            this.accessToken = this.calendarEl.dataset.accessToken;
            this.initCalendar();
            this.initFormHandler();
        }

        initCalendar() {
            // Simple date picker implementation
            const today = new Date();
            const maxDate = new Date();
            maxDate.setDate(maxDate.getDate() + 60); // Max 60 days ahead

            this.renderCalendar(today.getFullYear(), today.getMonth());
        }

        renderCalendar(year, month) {
            const firstDay = new Date(year, month, 1);
            const lastDay = new Date(year, month + 1, 0);
            const today = new Date();
            today.setHours(0, 0, 0, 0);

            const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                               'July', 'August', 'September', 'October', 'November', 'December'];

            let html = `
                <div class="o_appointment_date_nav">
                    <button type="button" class="o_nav_btn" id="prev-month">
                        <i class="fa fa-chevron-left"></i>
                    </button>
                    <span class="o_current_date">${monthNames[month]} ${year}</span>
                    <button type="button" class="o_nav_btn" id="next-month">
                        <i class="fa fa-chevron-right"></i>
                    </button>
                </div>
                <table class="table table-sm text-center">
                    <thead>
                        <tr>
                            <th>Sun</th><th>Mon</th><th>Tue</th><th>Wed</th><th>Thu</th><th>Fri</th><th>Sat</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            let day = 1;
            for (let i = 0; i < 6; i++) {
                html += '<tr>';
                for (let j = 0; j < 7; j++) {
                    if (i === 0 && j < firstDay.getDay()) {
                        html += '<td></td>';
                    } else if (day > lastDay.getDate()) {
                        html += '<td></td>';
                    } else {
                        const date = new Date(year, month, day);
                        const isPast = date < today;
                        const isSelected = this.selectedDate &&
                            date.toDateString() === this.selectedDate.toDateString();

                        let classes = 'o_calendar_day';
                        if (isPast) classes += ' disabled text-muted';
                        if (isSelected) classes += ' bg-primary text-white rounded';
                        if (!isPast && !isSelected) classes += ' cursor-pointer';

                        html += `<td class="${classes}"
                                     data-date="${date.toISOString().split('T')[0]}"
                                     ${isPast ? '' : 'role="button"'}>${day}</td>`;
                        day++;
                    }
                }
                html += '</tr>';
                if (day > lastDay.getDate()) break;
            }

            html += '</tbody></table>';
            this.calendarEl.innerHTML = html;

            // Event listeners
            this.calendarEl.querySelectorAll('.o_calendar_day:not(.disabled)').forEach(el => {
                el.addEventListener('click', (e) => this.selectDate(e.target.dataset.date));
            });

            document.getElementById('prev-month')?.addEventListener('click', () => {
                const newMonth = month === 0 ? 11 : month - 1;
                const newYear = month === 0 ? year - 1 : year;
                this.renderCalendar(newYear, newMonth);
            });

            document.getElementById('next-month')?.addEventListener('click', () => {
                const newMonth = month === 11 ? 0 : month + 1;
                const newYear = month === 11 ? year + 1 : year;
                this.renderCalendar(newYear, newMonth);
            });
        }

        async selectDate(dateStr) {
            this.selectedDate = new Date(dateStr + 'T00:00:00');
            this.selectedTime = null;

            // Update calendar UI
            this.calendarEl.querySelectorAll('.o_calendar_day').forEach(el => {
                el.classList.remove('bg-primary', 'text-white', 'rounded');
            });
            this.calendarEl.querySelector(`[data-date="${dateStr}"]`)
                ?.classList.add('bg-primary', 'text-white', 'rounded');

            // Fetch available slots
            await this.fetchSlots(dateStr);
        }

        async fetchSlots(dateStr) {
            const timeSlotsCard = document.getElementById('time-slots-card');
            const timeSlotsEl = document.getElementById('time-slots');

            if (!timeSlotsCard || !timeSlotsEl) return;

            timeSlotsCard.style.display = 'block';
            timeSlotsEl.innerHTML = '<div class="o_appointment_loading"><div class="spinner-border"></div><p class="mt-2">Loading available times...</p></div>';

            try {
                const response = await fetch(`/appointment/${this.accessToken}/slots`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        jsonrpc: '2.0',
                        method: 'call',
                        params: {
                            date: dateStr,
                            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                        },
                    }),
                });

                const data = await response.json();
                const result = data.result || data;

                if (result.error) {
                    timeSlotsEl.innerHTML = `<div class="alert alert-warning">${result.error}</div>`;
                    return;
                }

                this.renderSlots(result.slots || []);
            } catch (error) {
                console.error('Error fetching slots:', error);
                timeSlotsEl.innerHTML = '<div class="alert alert-danger">Error loading available times. Please try again.</div>';
            }
        }

        renderSlots(slots) {
            const timeSlotsEl = document.getElementById('time-slots');
            if (!timeSlotsEl) return;

            if (slots.length === 0) {
                timeSlotsEl.innerHTML = '<div class="alert alert-info">No available times for this date. Please select another date.</div>';
                return;
            }

            let html = '';
            slots.forEach(slot => {
                html += `
                    <div class="o_time_slot" data-datetime="${slot.datetime}" data-resources='${JSON.stringify(slot.available_resources)}'>
                        <div class="o_slot_time">${slot.time}</div>
                        <div class="o_slot_available">${slot.resource_count} available</div>
                    </div>
                `;
            });

            timeSlotsEl.innerHTML = html;

            // Add click handlers
            timeSlotsEl.querySelectorAll('.o_time_slot').forEach(el => {
                el.addEventListener('click', () => this.selectTime(el));
            });
        }

        selectTime(slotEl) {
            this.selectedTime = slotEl.dataset.datetime;
            const resources = JSON.parse(slotEl.dataset.resources || '[]');

            // Update UI
            document.querySelectorAll('.o_time_slot').forEach(el => {
                el.classList.remove('selected');
            });
            slotEl.classList.add('selected');

            // Auto-select first resource if only one
            if (resources.length === 1) {
                this.selectedResource = resources[0].id;
            } else if (resources.length > 1) {
                // Future enhancement: show resource selection UI when
                // multiple resources are available. For now, auto-select first.
                this.selectedResource = resources[0].id;
            }

            // Show booking form
            const formCard = document.getElementById('booking-form-card');
            if (formCard) {
                formCard.style.display = 'block';
            }

            // Update summary
            this.updateSummary();
        }

        updateSummary() {
            const summaryEl = document.getElementById('selected-datetime');
            if (!summaryEl) return;

            if (this.selectedDate && this.selectedTime) {
                const dt = new Date(this.selectedTime);
                const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
                const dateStr = dt.toLocaleDateString('en-US', options);
                const timeStr = dt.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
                summaryEl.innerHTML = `<strong>${dateStr}</strong><br/>at <strong>${timeStr}</strong>`;
            }
        }

        initFormHandler() {
            const form = document.getElementById('booking-form');
            if (!form) return;

            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.submitBooking(form);
            });
        }

        async submitBooking(form) {
            if (!this.selectedTime) {
                alert('Please select a date and time.');
                return;
            }

            const formData = new FormData(form);
            const submitBtn = form.querySelector('button[type="submit"]');

            // Collect question answers
            const answers = {};
            form.querySelectorAll('[name^="question_"]').forEach(input => {
                const questionId = input.name.replace('question_', '');
                answers[questionId] = input.type === 'checkbox' ? input.checked : input.value;
            });

            // Disable submit button
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa fa-spinner fa-spin me-2"></i>Booking...';

            try {
                const response = await fetch(`/appointment/${this.accessToken}/book`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        jsonrpc: '2.0',
                        method: 'call',
                        params: {
                            datetime_str: this.selectedTime,
                            resource_id: this.selectedResource,
                            name: formData.get('name'),
                            email: formData.get('email'),
                            phone: formData.get('phone'),
                            notes: formData.get('notes'),
                            answers: answers,
                        },
                    }),
                });

                const data = await response.json();
                const result = data.result || data;

                if (result.error) {
                    alert('Error: ' + result.error);
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fa fa-check me-2"></i>Confirm Booking';
                    return;
                }

                if (result.success && result.redirect_url) {
                    window.location.href = `/appointment/confirm/${result.access_token}`;
                }
            } catch (error) {
                console.error('Booking error:', error);
                alert('An error occurred. Please try again.');
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fa fa-check me-2"></i>Confirm Booking';
            }
        }
    }

    // Export for use in other modules
    window.AppointmentBookingApp = AppointmentBookingApp;
})();
