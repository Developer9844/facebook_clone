const express = require('express');
const bodyParser = require('body-parser');
const session = require('express-session');
const axios = require('axios');
require('dotenv').config;

const app = express();
const PORT = 3000;
const API_BASE_URL = process.env.API_BASE_URL || 'http://127.0.0.1:5000';

app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.static('public'));
app.use(session({ secret: 'mysecret', resave: false, saveUninitialized: true }));
app.set('view engine', 'ejs');

// Redirect to login page
app.get('/', (req, res) => res.redirect('/login'));

// Render login page
app.get('/login', (req, res) => res.render('login', { error: null }));

// Handle login form submission
app.post('/login', async (req, res) => {
    try {
        const { username, password } = req.body;
        const response = await axios.post(`${API_BASE_URL}/api/login`, { username, password });
        req.session.user = response.data;
        req.session.token = response.data.access_token;
        res.redirect('/dashboard');
    } catch (error) {
        res.render('login', { error: 'Invalid credentials' });
    }
});

// Render registration page
app.get('/register', (req, res) => res.render('register', { error: null }));

// Handle registration form submission
app.post('/register', async (req, res) => {
    try {
        const { username, password, full_name } = req.body;
        await axios.post(`${API_BASE_URL}/api/register`, { username, password, full_name });
        res.redirect('/login');
    } catch (error) {
        res.render('register', { error: 'Registration failed' });
    }
});

// Render dashboard with posts
app.get('/dashboard', async (req, res) => {
    if (!req.session.user || !req.session.token) return res.redirect('/login');

    try {
        const response = await axios.get(`${API_BASE_URL}/api/posts/full`, {
            headers: { Authorization: `Bearer ${req.session.token}` }
        });

        res.render('dashboard', { user: req.session.user, posts: response.data, error: null });
    } catch (error) {
        console.error("Error fetching posts:", error.response ? error.response.data : error.message);
        res.render('dashboard', { user: req.session.user, posts: [], error: "Failed to fetch posts." });
    }
});

app.post('/dashboard/add-post', async (req, res) => {
    if (!req.session.user || !req.session.token) return res.redirect('/login');

    const { content } = req.body;

    try {
        await axios.post(`${API_BASE_URL}/api/posts`,
            { content },
            { headers: { Authorization: `Bearer ${req.session.token}` } }
        );

        res.redirect('/dashboard');
    } catch (error) {
        console.error("Error adding post:", error.response ? error.response.data : error.message);
        res.render('dashboard', { user: req.session.user, error: "Failed to add post.", success: null });
    }
});

app.post('/update-post', async (req, res) => {
    if (!req.session.user || !req.session.token) return res.redirect('/login');

    const { post_id, content } = req.body;

    try {
        await axios.put(`${API_BASE_URL}/api/posts/${post_id}`,
            { content },
            { headers: { Authorization: `Bearer ${req.session.token}` } }
        );
        res.redirect('/profile'); // Refresh page after update
    } catch (error) {
        console.error("Error updating post:", error.response ? error.response.data : error.message);
        res.redirect('/profile');
    }
});

app.post('/delete-post', async (req, res) => {
    if (!req.session.user || !req.session.token) return res.redirect('/login');

    const { post_id } = req.body;

    try {
        await axios.delete(`${API_BASE_URL}/api/posts/${post_id}`, {
            headers: { Authorization: `Bearer ${req.session.token}` }
        });
        res.redirect('/profile'); // Refresh page after deletion
    } catch (error) {
        console.error("Error deleting post:", error.response ? error.response.data : error.message);
        res.redirect('/profile');
    }
});

app.get('/profile', async (req, res) => {
    if (!req.session.user || !req.session.token) return res.redirect('/login');

    try {
        const [profileResponse, postsResponse] = await Promise.all([
            axios.get(`${API_BASE_URL}/api/profile`, {
                headers: { Authorization: `Bearer ${req.session.token}` }
            }),
            axios.get(`${API_BASE_URL}/api/my-posts`, {
                headers: { Authorization: `Bearer ${req.session.token}` }
            })
        ]);

        const user = profileResponse.data;
        user.posts = postsResponse.data; // Attach posts to user object
        

        res.render('profile', { user: req.session.user, error: null, success: "Post updated successfully." });
    } catch (error) {
        console.error("Error fetching profile or posts:", error.response ? error.response.data : error.message);
        res.render('profile', { user: {}, error: "Failed to fetch profile data.", success: null });
    }
});

app.post('/profile/update', async (req, res) => {
    if (!req.session.user || !req.session.token) return res.redirect('/login');

    const { username, full_name, bio } = req.body;
    try {
        await axios.put(`${API_BASE_URL}/api/profile`,
            { username, full_name, bio },
            { headers: { Authorization: `Bearer ${req.session.token}` } }
        );

        req.session.user.username = username;
        req.session.user.full_name = full_name;
        res.render('profile', { user: req.session.user, error: null, success: "Profile updated successfully." });
        
    } catch (error) {
        console.error("Error updating profile:", error.response ? error.response.data : error.message);
        res.render('profile', { user: req.session.user, error: "Failed to update profile.", success: null });
    }
});

app.post('/profile/change-password', async (req, res) => {
    if (!req.session.user || !req.session.token) return res.redirect('/login');

    const { old_password, new_password } = req.body;
    try {
        await axios.put(`${API_BASE_URL}/api/profile`,
            { old_password, new_password },
            { headers: { Authorization: `Bearer ${req.session.token}` } }
        );
        res.render('profile', { user: req.session.user, error: null, success: "Password changed successfully." });
    } catch (error) {
        console.error("Error changing password:", error.response ? error.response.data : error.message);
        res.render('profile', { user: req.session.user, error: "Failed to change password.", success: null });
    }
});




// Logout route
app.get('/logout', (req, res) => {
    req.session.destroy(() => res.redirect('/login'));
});

app.listen(PORT, () => console.log(`Server running on http://localhost:${PORT}`));
