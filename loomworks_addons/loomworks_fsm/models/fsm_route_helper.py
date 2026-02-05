# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from math import radians, sin, cos, sqrt, atan2

from odoo import api, models


class FSMRouteHelper(models.TransientModel):
    """
    FSM Route Helper - Provides basic route optimization suggestions.

    Uses nearest-neighbor heuristic to suggest task order.
    For production use, integrate with Google Maps Directions API or similar.
    """
    _name = 'fsm.route.helper'
    _description = 'FSM Route Helper'

    @api.model
    def get_suggested_route(self, task_ids, start_location=None):
        """
        Returns tasks ordered by proximity using nearest-neighbor heuristic.

        Args:
            task_ids: List of task IDs to optimize
            start_location: Optional tuple (latitude, longitude) for starting point

        Returns:
            list: Task IDs in suggested order
        """
        tasks = self.env['project.task'].browse(task_ids)

        if not tasks:
            return []

        # Filter tasks that have location data
        tasks_with_location = tasks.filtered(
            lambda t: t.partner_latitude and t.partner_longitude
        )
        tasks_without_location = tasks - tasks_with_location

        if not tasks_with_location:
            # No location data, return original order
            return task_ids

        # Determine starting point
        if start_location:
            current_lat, current_lng = start_location
        else:
            # Use company location or first task
            company = self.env.company
            if company.partner_id.partner_latitude and company.partner_id.partner_longitude:
                current_lat = company.partner_id.partner_latitude
                current_lng = company.partner_id.partner_longitude
            else:
                first_task = tasks_with_location[0]
                current_lat = first_task.partner_latitude
                current_lng = first_task.partner_longitude

        # Nearest neighbor algorithm
        ordered = []
        remaining = list(tasks_with_location)

        while remaining:
            # Find nearest task
            nearest = min(remaining, key=lambda t: self._distance(
                current_lat, current_lng,
                t.partner_latitude, t.partner_longitude
            ))
            ordered.append(nearest.id)
            current_lat = nearest.partner_latitude
            current_lng = nearest.partner_longitude
            remaining.remove(nearest)

        # Add tasks without location at the end
        ordered.extend(tasks_without_location.ids)

        return ordered

    @api.model
    def _distance(self, lat1, lng1, lat2, lng2):
        """
        Calculate distance between two points using Haversine formula.

        Args:
            lat1, lng1: First point coordinates
            lat2, lng2: Second point coordinates

        Returns:
            float: Distance in kilometers
        """
        R = 6371  # Earth's radius in kilometers

        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])

        dlat = lat2 - lat1
        dlng = lng2 - lng1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c

    @api.model
    def get_route_summary(self, task_ids, start_location=None):
        """
        Get route summary with distances and estimated time.

        Args:
            task_ids: List of task IDs in desired order
            start_location: Optional starting point

        Returns:
            dict: Route summary with total distance and tasks
        """
        tasks = self.env['project.task'].browse(task_ids)

        if not tasks:
            return {'total_distance': 0, 'tasks': []}

        # Calculate starting point
        if start_location:
            current_lat, current_lng = start_location
        else:
            company = self.env.company
            current_lat = company.partner_id.partner_latitude or 0
            current_lng = company.partner_id.partner_longitude or 0

        total_distance = 0
        route_tasks = []

        for task in tasks:
            task_lat = task.partner_latitude or 0
            task_lng = task.partner_longitude or 0

            if task_lat and task_lng and current_lat and current_lng:
                distance = self._distance(current_lat, current_lng, task_lat, task_lng)
            else:
                distance = 0

            route_tasks.append({
                'id': task.id,
                'name': task.name,
                'partner': task.partner_id.name if task.partner_id else '',
                'address': task.partner_id._display_address(without_company=True) if task.partner_id else '',
                'distance_from_previous': round(distance, 2),
                'has_location': bool(task_lat and task_lng),
            })

            total_distance += distance
            current_lat = task_lat or current_lat
            current_lng = task_lng or current_lng

        return {
            'total_distance': round(total_distance, 2),
            'estimated_drive_time_minutes': round(total_distance / 50 * 60),  # Assume 50 km/h average
            'tasks': route_tasks,
        }
