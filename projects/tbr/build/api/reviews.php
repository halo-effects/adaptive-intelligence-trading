<?php
/**
 * TrustedBusinessReviews.com — Review API
 * Flat-file JSON storage with rate limiting and admin auth
 */

header('Content-Type: application/json');
header('X-Content-Type-Options: nosniff');

// CORS for same-origin
$origin = isset($_SERVER['HTTP_ORIGIN']) ? $_SERVER['HTTP_ORIGIN'] : '';
if (strpos($origin, 'trustedbusinessreviews.com') !== false) {
    header("Access-Control-Allow-Origin: $origin");
}
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, X-CSRF-Token');
header('Access-Control-Allow-Credentials: true');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit(0); }

// ── Config ──
define('DATA_DIR', dirname(__DIR__) . '/data');
define('REVIEWS_FILE', DATA_DIR . '/reviews.json');
define('RATE_FILE', DATA_DIR . '/rate_limits.json');
define('SESSIONS_DIR', DATA_DIR . '/sessions');
define('ADMIN_CREDS_FILE', DATA_DIR . '/admin_creds.json');
define('RATE_LIMIT', 3); // per IP per hour
define('SESSION_LIFETIME', 86400); // 24 hours

// Ensure dirs exist
if (!is_dir(DATA_DIR)) mkdir(DATA_DIR, 0755, true);
if (!is_dir(SESSIONS_DIR)) mkdir(SESSIONS_DIR, 0755, true);

// ── Helpers ──
function loadJson($file) {
    if (!file_exists($file)) return [];
    $fp = fopen($file, 'r');
    if (!$fp) return [];
    flock($fp, LOCK_SH);
    $data = json_decode(fread($fp, max(filesize($file), 1)), true);
    flock($fp, LOCK_UN);
    fclose($fp);
    return is_array($data) ? $data : [];
}

function saveJson($file, $data) {
    $fp = fopen($file, 'c');
    if (!$fp) return false;
    flock($fp, LOCK_EX);
    ftruncate($fp, 0);
    fwrite($fp, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
    fflush($fp);
    flock($fp, LOCK_UN);
    fclose($fp);
    return true;
}

function sanitize($str, $maxLen = 1000) {
    $str = trim($str);
    $str = mb_substr($str, 0, $maxLen);
    $str = htmlspecialchars($str, ENT_QUOTES, 'UTF-8');
    return $str;
}

function getIP() {
    return $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';
}

function respond($data, $code = 200) {
    http_response_code($code);
    echo json_encode($data);
    exit;
}

function checkRateLimit() {
    $ip = getIP();
    $now = time();
    $rates = loadJson(RATE_FILE);
    
    // Clean old entries
    $rates = array_filter($rates, function($entry) use ($now) {
        return ($now - $entry['time']) < 3600;
    });
    
    // Count for this IP
    $count = 0;
    foreach ($rates as $entry) {
        if ($entry['ip'] === $ip) $count++;
    }
    
    if ($count >= RATE_LIMIT) {
        respond(['error' => 'Too many submissions. Please try again later.'], 429);
    }
    
    // Add entry
    $rates[] = ['ip' => $ip, 'time' => $now];
    saveJson(RATE_FILE, array_values($rates));
}

// ── CSRF ──
function generateCSRF() {
    if (session_status() === PHP_SESSION_NONE) {
        session_set_cookie_params(['httponly' => true, 'secure' => true, 'samesite' => 'Strict']);
        session_start();
    }
    if (empty($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf_token'];
}

function verifyCSRF() {
    if (session_status() === PHP_SESSION_NONE) {
        session_set_cookie_params(['httponly' => true, 'secure' => true, 'samesite' => 'Strict']);
        session_start();
    }
    $token = $_SERVER['HTTP_X_CSRF_TOKEN'] ?? $_POST['csrf_token'] ?? '';
    if (empty($_SESSION['csrf_token']) || !hash_equals($_SESSION['csrf_token'], $token)) {
        respond(['error' => 'Invalid security token. Please refresh and try again.'], 403);
    }
}

// ── Admin Auth ──
function getAdminCreds() {
    if (!file_exists(ADMIN_CREDS_FILE)) {
        // Default credentials — CHANGE THESE
        $creds = [
            'username' => 'admin',
            'password_hash' => password_hash('TBR-Admin-2026!', PASSWORD_BCRYPT)
        ];
        saveJson(ADMIN_CREDS_FILE, $creds);
        return $creds;
    }
    return loadJson(ADMIN_CREDS_FILE);
}

function adminLogin($username, $password) {
    $creds = getAdminCreds();
    if ($username === $creds['username'] && password_verify($password, $creds['password_hash'])) {
        $sessionId = bin2hex(random_bytes(32));
        $sessionFile = SESSIONS_DIR . '/' . $sessionId . '.json';
        saveJson($sessionFile, [
            'created' => time(),
            'ip' => getIP(),
            'username' => $username
        ]);
        return $sessionId;
    }
    return false;
}

function requireAdmin() {
    $token = '';
    // Check Authorization header
    if (isset($_SERVER['HTTP_AUTHORIZATION'])) {
        $token = str_replace('Bearer ', '', $_SERVER['HTTP_AUTHORIZATION']);
    }
    // Check cookie
    if (!$token && isset($_COOKIE['tbr_admin_session'])) {
        $token = $_COOKIE['tbr_admin_session'];
    }
    
    if (!$token) respond(['error' => 'Authentication required'], 401);
    
    $sessionFile = SESSIONS_DIR . '/' . $token . '.json';
    if (!file_exists($sessionFile)) respond(['error' => 'Invalid session'], 401);
    
    $session = loadJson($sessionFile);
    if ((time() - $session['created']) > SESSION_LIFETIME) {
        unlink($sessionFile);
        respond(['error' => 'Session expired'], 401);
    }
    
    return $session;
}

// ── Initialize reviews file ──
if (!file_exists(REVIEWS_FILE)) {
    saveJson(REVIEWS_FILE, []);
}

// ── Route ──
$action = $_GET['action'] ?? $_POST['action'] ?? '';

switch ($action) {
    case 'csrf':
        $token = generateCSRF();
        respond(['token' => $token]);
        break;

    case 'submit':
        if ($_SERVER['REQUEST_METHOD'] !== 'POST') respond(['error' => 'POST required'], 405);
        
        verifyCSRF();
        checkRateLimit();
        
        // Get input (support both form data and JSON)
        $contentType = $_SERVER['CONTENT_TYPE'] ?? '';
        if (strpos($contentType, 'application/json') !== false) {
            $input = json_decode(file_get_contents('php://input'), true) ?: [];
        } else {
            $input = $_POST;
        }
        
        $name = sanitize($input['reviewer_name'] ?? '', 100);
        $email = filter_var($input['reviewer_email'] ?? '', FILTER_VALIDATE_EMAIL);
        $rating = intval($input['rating'] ?? 0);
        $text = sanitize($input['review_text'] ?? '', 5000);
        $businessSlug = sanitize($input['business_slug'] ?? '', 200);
        $categorySlug = sanitize($input['category_slug'] ?? '', 200);
        
        // Validate
        $errors = [];
        if (strlen($name) < 2) $errors[] = 'Name is required (min 2 characters)';
        if (!$email) $errors[] = 'Valid email is required';
        if ($rating < 1 || $rating > 5) $errors[] = 'Rating must be 1-5';
        if (strlen($text) < 10) $errors[] = 'Review must be at least 10 characters';
        if (!$businessSlug) $errors[] = 'Business is required';
        if (!$categorySlug) $errors[] = 'Category is required';
        
        if ($errors) respond(['error' => implode('. ', $errors)], 400);
        
        $review = [
            'id' => bin2hex(random_bytes(8)),
            'reviewer_name' => $name,
            'reviewer_email' => $email,
            'rating' => $rating,
            'text' => $text,
            'business_slug' => $businessSlug,
            'category_slug' => $categorySlug,
            'status' => 'pending',
            'ip' => getIP(),
            'submitted_at' => date('Y-m-d H:i:s'),
            'moderated_at' => null
        ];
        
        $reviews = loadJson(REVIEWS_FILE);
        $reviews[] = $review;
        saveJson(REVIEWS_FILE, $reviews);
        
        respond(['success' => true, 'message' => 'Thank you! Your review has been submitted and is pending approval.']);
        break;

    case 'get':
        $business = sanitize($_GET['business'] ?? '', 200);
        if (!$business) respond(['error' => 'Business slug required'], 400);
        
        $reviews = loadJson(REVIEWS_FILE);
        $filtered = array_values(array_filter($reviews, function($r) use ($business) {
            return $r['business_slug'] === $business && $r['status'] === 'approved';
        }));
        
        // Sort newest first, remove private fields
        usort($filtered, function($a, $b) {
            return strcmp($b['submitted_at'], $a['submitted_at']);
        });
        
        $public = array_map(function($r) {
            return [
                'id' => $r['id'],
                'reviewer_name' => $r['reviewer_name'],
                'rating' => $r['rating'],
                'text' => $r['text'],
                'date' => $r['submitted_at']
            ];
        }, $filtered);
        
        respond(['reviews' => $public, 'count' => count($public)]);
        break;

    case 'login':
        if ($_SERVER['REQUEST_METHOD'] !== 'POST') respond(['error' => 'POST required'], 405);
        
        $contentType = $_SERVER['CONTENT_TYPE'] ?? '';
        if (strpos($contentType, 'application/json') !== false) {
            $input = json_decode(file_get_contents('php://input'), true) ?: [];
        } else {
            $input = $_POST;
        }
        
        $username = $input['username'] ?? '';
        $password = $input['password'] ?? '';
        
        $sessionId = adminLogin($username, $password);
        if ($sessionId) {
            setcookie('tbr_admin_session', $sessionId, [
                'expires' => time() + SESSION_LIFETIME,
                'path' => '/',
                'httponly' => true,
                'secure' => true,
                'samesite' => 'Strict'
            ]);
            respond(['success' => true, 'session' => $sessionId]);
        } else {
            respond(['error' => 'Invalid credentials'], 401);
        }
        break;

    case 'logout':
        $token = $_COOKIE['tbr_admin_session'] ?? '';
        if ($token) {
            $sessionFile = SESSIONS_DIR . '/' . $token . '.json';
            if (file_exists($sessionFile)) unlink($sessionFile);
            setcookie('tbr_admin_session', '', ['expires' => 1, 'path' => '/']);
        }
        respond(['success' => true]);
        break;

    case 'pending':
        requireAdmin();
        $reviews = loadJson(REVIEWS_FILE);
        $pending = array_values(array_filter($reviews, function($r) {
            return $r['status'] === 'pending';
        }));
        usort($pending, function($a, $b) {
            return strcmp($b['submitted_at'], $a['submitted_at']);
        });
        respond(['reviews' => $pending, 'count' => count($pending)]);
        break;

    case 'all':
        requireAdmin();
        $reviews = loadJson(REVIEWS_FILE);
        
        // Filters
        $status = $_GET['status'] ?? '';
        $business = $_GET['business'] ?? '';
        $category = $_GET['category'] ?? '';
        $search = $_GET['search'] ?? '';
        
        if ($status) $reviews = array_filter($reviews, function($r) use ($status) { return $r['status'] === $status; });
        if ($business) $reviews = array_filter($reviews, function($r) use ($business) { return $r['business_slug'] === $business; });
        if ($category) $reviews = array_filter($reviews, function($r) use ($category) { return $r['category_slug'] === $category; });
        if ($search) {
            $search = strtolower($search);
            $reviews = array_filter($reviews, function($r) use ($search) {
                return strpos(strtolower($r['reviewer_name'] ?? ''), $search) !== false 
                    || strpos(strtolower($r['text'] ?? ''), $search) !== false
                    || strpos(strtolower($r['business_slug'] ?? ''), $search) !== false;
            });
        }
        
        $reviews = array_values($reviews);
        usort($reviews, function($a, $b) {
            return strcmp($b['submitted_at'], $a['submitted_at']);
        });
        
        respond(['reviews' => $reviews, 'count' => count($reviews)]);
        break;

    case 'stats':
        requireAdmin();
        $reviews = loadJson(REVIEWS_FILE);
        $stats = ['total' => count($reviews), 'pending' => 0, 'approved' => 0, 'rejected' => 0, 'businesses' => []];
        foreach ($reviews as $r) {
            $s = $r['status'] ?? 'unknown';
            if (isset($stats[$s])) $stats[$s]++;
            $biz = $r['business_slug'] ?? 'unknown';
            if (!isset($stats['businesses'][$biz])) $stats['businesses'][$biz] = 0;
            $stats['businesses'][$biz]++;
        }
        respond($stats);
        break;

    case 'moderate':
        if ($_SERVER['REQUEST_METHOD'] !== 'POST') respond(['error' => 'POST required'], 405);
        requireAdmin();
        
        $contentType = $_SERVER['CONTENT_TYPE'] ?? '';
        if (strpos($contentType, 'application/json') !== false) {
            $input = json_decode(file_get_contents('php://input'), true) ?: [];
        } else {
            $input = $_POST;
        }
        
        $reviewId = $input['review_id'] ?? '';
        $newStatus = $input['status'] ?? '';
        
        if (!$reviewId || !in_array($newStatus, ['approved', 'rejected'])) {
            respond(['error' => 'review_id and status (approved/rejected) required'], 400);
        }
        
        $reviews = loadJson(REVIEWS_FILE);
        $found = false;
        foreach ($reviews as &$r) {
            if ($r['id'] === $reviewId) {
                $r['status'] = $newStatus;
                $r['moderated_at'] = date('Y-m-d H:i:s');
                $found = true;
                break;
            }
        }
        unset($r);
        
        if (!$found) respond(['error' => 'Review not found'], 404);
        
        saveJson(REVIEWS_FILE, $reviews);
        respond(['success' => true, 'message' => "Review $newStatus"]);
        break;

    case 'check':
        // Auth check for admin dashboard
        $session = requireAdmin();
        respond(['authenticated' => true, 'username' => $session['username'] ?? 'admin']);
        break;

    default:
        respond(['error' => 'Unknown action', 'available' => ['csrf', 'submit', 'get', 'login', 'logout', 'pending', 'all', 'stats', 'moderate', 'check']], 400);
}
