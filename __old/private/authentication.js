var db = require("./db"),
    crypto = require("crypto"),
    User = require("./models/user").User,
    passport = require("passport"),
    LocalStrategy = require("passport-local").Strategy,
    GoogleStrategy = require("passport-google").Strategy,
    TwitterStrategy = require("passport-twitter").Strategy,
    FacebookStrategy = require("passport-facebook").Strategy;

exports.init = function(app) {

    passport.use(createLocalStrategy());
    passport.use("google-login", createGoogleStrategy(app, "/login/google/return"));
    passport.use("google-register", createGoogleStrategy(app, "/register/google/return"));
    passport.use("twitter-login", createTwitterStrategy(app, "/login/twitter/return"));
    passport.use("twitter-register", createTwitterStrategy(app, "/register/twitter/return"));
    passport.use("facebook-login", createFacebookStrategy(app, "/login/facebook/return"));
    passport.use("facebook-register", createFacebookStrategy(app, "/register/facebook/return"));

    passport.serializeUser(function(user, done) {
        done(null, JSON.stringify(user));
    });

    passport.deserializeUser(function(user, done) {
        done(null, new User(JSON.parse(user)));
    });
};

exports.login = {
    local: function(req, res) {
        passport.authenticate("local", function (err, user) {

            if (err)
                return res.json({ error: res.__("Login error") });
            else if (!user)
                return res.json({ error: res.__("Login failed") });

            req.login(user, function(err) {
                if (err)
                    return res.json({ error: res.__("Login error") });

                return res.json({ success: true });
            });

        })(req, res);
    },

    google: {
        init: passport.authenticate("google-login"),
        "return": passport.authenticate("google-login", {
            successRedirect: "/",
            failureRedirect: "/login?fail=Google"
        })
    },

    twitter: {
        init: passport.authenticate("twitter-login"),
        "return": passport.authenticate("twitter-login", {
            successRedirect: "/",
            failureRedirect: "/login?fail=Twitter"
        })
    },

    facebook: {
        init: passport.authenticate("facebook-login"),
        "return": passport.authenticate("facebook-login", {
            successRedirect: "/",
            failureRedirect: "/login?fail=Facebook"
        })
    }
};

exports.register = {
    google: {
        init: passport.authenticate("google-register"),
        "return": passport.authenticate("google-register", {
            successRedirect: "/",
            failureRedirect: "/register"
        })
    },
    twitter: {
        init: passport.authenticate("twitter-register"),
        "return": passport.authenticate("twitter-register", {
            successRedirect: "/",
            failureRedirect: "/register"
        })
    },
    facebook: {
        init: passport.authenticate("facebook-register"),
        "return": passport.authenticate("facebook-register", {
            successRedirect: "/",
            failureRedirect: "/register"
        })
    }
};

exports.logout = function(req, res) {
	req.logout();
	res.end();
};

function createLocalStrategy() {
    return new LocalStrategy(
        function(email, password, done) {

            var passwordHash = crypto.createHash('md5').update(password).digest("hex");

            db.getUser(email)
                .then(function (user) {
                    if (user && user.password === passwordHash)
                        done(null, new User(user));
                    else
                        done(null, false);
                },
                done.bind(null, null, false));
        }
    )
}

function createGoogleStrategy(app, returnUrl) {
    return new GoogleStrategy({
            returnURL: app.get("url") + returnUrl,
            realm: app.get("url"),
            passReqToCallback: true
        },
        function(req, identifier, profile, done) {

            db.getUserByAuthToken(identifier)
                .then(function (user) {
                    if (user)
                        done(null, new User(user));
                    else {
                        req.session.registrationInfo = {
                            google: {
                                identifier: identifier,
                                profile: profile
                            }
                        };
                        done(null, false);
                    }
                },
                done.bind(null, null, false));
        });
}

function createTwitterStrategy(app, returnUrl) {
    return new TwitterStrategy({
            consumerKey: process.env.TWITTER_KEY,
            consumerSecret: process.env.TWITTER_SECRET,
            callbackURL: app.get("url") + returnUrl,
            passReqToCallback: true
        },
        function(req, token, tokenSecret, profile, done) {
            if (!profile.id)
                done(null, false);

            var identifier = "twitter://" + profile.id;

            db.getUserByAuthToken(identifier)
                .then(function (user) {
                    if (user)
                        done(null, new User(user));
                    else {
                        req.session.registrationInfo = {
                            twitter: {
                                identifier: identifier,
                                profile: profile
                            }
                        };
                        done(null, false);
                    }
                },
                done.bind(null, null, false));
        });
}

function createFacebookStrategy(app, returnUrl) {
    return new FacebookStrategy({
            clientID: process.env.FACEBOOK_APP_ID,
            clientSecret: process.env.FACEBOOK_APP_SECRET,
            callbackURL: app.get("url") + returnUrl,
            passReqToCallback: true
        },
        function(req, accessToken, refreshToken, profile, done) {
            if (!profile.id)
                done(null, false);

            var identifier = "facebook://" + profile.id;

            db.getUserByAuthToken(identifier)
                .then(function (user) {
                    if (user)
                        done(null, new User(user));
                    else {
                        req.session.registrationInfo = {
                            facebook: {
                                identifier: identifier,
                                profile: profile
                            }
                        };
                        done(null, false);
                    }
                },
                done.bind(null, null, false));
        });
}