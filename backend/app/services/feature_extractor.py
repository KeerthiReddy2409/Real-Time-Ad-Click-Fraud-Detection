import numpy as np
from scipy.spatial.distance import euclidean
from scipy.stats import entropy

def extract_features_from_events(mouse_events):
    """
    Extract 30+ physics features from raw mouse events.
    mouse_events: list of dicts with 'x', 'y', 'timestamp'
    Returns: dict of features or None if insufficient data
    """
    if len(mouse_events) < 3:
        return None

    xs = [e.x for e in mouse_events]
    ys = [e.y for e in mouse_events]
    ts = [e.timestamp for e in mouse_events]
    points = list(zip(xs, ys, ts))

    # Total distance
    total_distance = sum(
        euclidean((xs[i-1], ys[i-1]), (xs[i], ys[i]))
        for i in range(1, len(points))
    )
    straight_distance = euclidean((xs[0], ys[0]), (xs[-1], ys[-1]))
    path_efficiency = straight_distance / total_distance if total_distance > 0 else 1.0

    # Velocities
    velocities = []
    for i in range(1, len(points)):
        dt = ts[i] - ts[i-1]
        if dt > 0:
            velocities.append(euclidean((xs[i-1], ys[i-1]), (xs[i], ys[i])) / dt)
    if not velocities:
        return None

    avg_velocity = np.mean(velocities)
    max_velocity = np.max(velocities)
    velocity_variance = np.var(velocities)
    vel_hist, _ = np.histogram(velocities, bins=10, density=True)
    vel_entropy = entropy(vel_hist + 1e-10)
    initial_velocity = velocities[0]
    final_velocity = velocities[-1]
    velocity_ratio = final_velocity / (initial_velocity + 1e-10)

    # Accelerations
    accelerations = []
    for i in range(1, len(velocities)):
        dt = ts[i] - ts[i-1]
        if dt > 0:
            accelerations.append((velocities[i] - velocities[i-1]) / dt)
    avg_acceleration = np.mean(accelerations) if accelerations else 0
    max_acceleration = np.max(accelerations) if accelerations else 0
    acc_variance = np.var(accelerations) if accelerations else 0
    acc_sign_changes = sum(1 for i in range(1, len(accelerations)) if accelerations[i] * accelerations[i-1] < 0)
    acc_sign_change_rate = acc_sign_changes / max(len(accelerations)-1, 1)

    # Jerk
    jerks = []
    for i in range(1, len(accelerations)):
        dt = ts[i] - ts[i-1]
        if dt > 0:
            jerks.append((accelerations[i] - accelerations[i-1]) / dt)
    avg_jerk = np.mean(jerks) if jerks else 0
    jerk_variance = np.var(jerks) if jerks else 0
    max_jerk = np.max(np.abs(jerks)) if jerks else 0

    # Angle changes
    angles = []
    for i in range(1, len(points)-1):
        v1 = (xs[i] - xs[i-1], ys[i] - ys[i-1])
        v2 = (xs[i+1] - xs[i], ys[i+1] - ys[i])
        dot = v1[0]*v2[0] + v1[1]*v2[1]
        mag1 = np.sqrt(v1[0]**2 + v1[1]**2)
        mag2 = np.sqrt(v2[0]**2 + v2[1]**2)
        if mag1 > 0 and mag2 > 0:
            cos_angle = np.clip(dot / (mag1 * mag2), -1.0, 1.0)
            angles.append(np.arccos(cos_angle))
    avg_angle_change = np.mean(angles) if angles else 0
    angle_variance = np.var(angles) if angles else 0
    max_angle = np.max(angles) if angles else 0

    # Curvature
    curvatures = []
    for i in range(1, len(points)-1):
        a = euclidean((xs[i-1], ys[i-1]), (xs[i], ys[i]))
        b = euclidean((xs[i], ys[i]), (xs[i+1], ys[i+1]))
        c = euclidean((xs[i+1], ys[i+1]), (xs[i-1], ys[i-1]))
        s = (a+b+c)/2
        area = np.sqrt(max(s*(s-a)*(s-b)*(s-c), 0))
        if area > 0:
            curvatures.append(1.0 / ((a*b*c) / (4*area)))
    avg_curvature = np.mean(curvatures) if curvatures else 0
    max_curvature = np.max(curvatures) if curvatures else 0
    curvature_variance = np.var(curvatures) if curvatures else 0

    # Pauses
    pauses = 0
    total_pause_time = 0
    for i in range(1, len(ts)):
        dt = ts[i] - ts[i-1]
        if dt > 100:
            pauses += 1
            total_pause_time += dt
    total_time = ts[-1] - ts[0]
    pause_ratio = total_pause_time / total_time if total_time > 0 else 0

    return {
        'total_distance': total_distance,
        'straight_distance': straight_distance,
        'path_efficiency': path_efficiency,
        'avg_velocity': avg_velocity,
        'max_velocity': max_velocity,
        'velocity_variance': velocity_variance,
        'vel_entropy': vel_entropy,
        'initial_velocity': initial_velocity,
        'final_velocity': final_velocity,
        'velocity_ratio': velocity_ratio,
        'avg_acceleration': avg_acceleration,
        'max_acceleration': max_acceleration,
        'acc_variance': acc_variance,
        'acc_sign_change_rate': acc_sign_change_rate,
        'avg_jerk': avg_jerk,
        'jerk_variance': jerk_variance,
        'max_jerk': max_jerk,
        'avg_angle_change': avg_angle_change,
        'angle_variance': angle_variance,
        'max_angle': max_angle,
        'avg_curvature': avg_curvature,
        'max_curvature': max_curvature,
        'curvature_variance': curvature_variance,
        'pause_count': pauses,
        'pause_duration': total_pause_time,
        'pause_ratio': pause_ratio,
        'total_time': total_time,
        'num_points': len(points)
    }