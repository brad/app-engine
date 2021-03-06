MayOne.us RELOADED
==================

We're trying a different architecture on GAE.

This project is licensed under the Apache License, version 2.

HELP NEEDED!
------------
If you know a thing or two about computers and youre're interested in 
contributing, check out https://github.com/MayOneUS/wiki/wiki

Design sketch
-------------

The majority of the site is just basic static content, as it should
be. That markup lives in "markup/" in the form of jade files. If you
don't know what those are, they're very simple, and remove literally
50% of HTML's boilerplate so they're worth it. Read the 3 minute
tutorial.

Stylesheets are in "stylesheets/" as sass files. See last paragraph
for why that's good.

Ideally there will be little enough JS that no framework will be necessary (fingers crossed).

The backend will be very simple with two endpoints

1. Pledge. This has to be done in coordination with stripe so that stripe stores the credit card info, and we only store an opaque token and the pledge amount. This will write to what'll be probably the only table in the datastore.
2. GetTotal: Simple sum over pledges. Store it in memcache, expire every few minutes. Boom.

Dependencies
------------
* Python App Engine SDK
* NPM
* sass (with ruby installed, `gem install sass`)

Hacking
-------
After checking out the code, run `npm install`. To start the server, run `npm start` and go to http://localhost:8080. That's it!

If you want to rapidly set up a development environment that already has npm and
dependencies installed using docker, try running

```
docker run -t -i -v /path/to/repo:/development jtolds/mayone-gae /bin/bash
```

Deploying
---------
We have 4 deployment environments available, all of which can be set up with grunt (installed by npm).
* **local**: For normal development, with code updates on every reload. Run `npm start` or equivalently `node_modules/.bin/grunt local`.
  * Note that in local mode, you can't actually send a transaction to stripe due to an SSL bug in dev_appserver. But 
    you can get right up to that point before it fails, which is generally good enough.
* **dev**: This is an independant instance of the app running at https://pure-spring-568.appspot.com. We can do 
  whatever we want here because the data's all fake. It also uses Stripe's test keys, so feel free to submit test 
  transactions with credit card 4242 4242 4242 4242. To deploy, run `./node_modules/.bin/grunt dev`, and then 
  `appcfg.py --oauth2 update build/`.
* **staging**: This is the real app, but a separate version that's available at https://staging-dot-mayday-pac.appspot.com/.
  Notably, it uses the same datastore as prod, and the real stripe keys. Any code that touches 
  the data should be deployed here with caution, but if not, you can be a little lax since real 
  traffic doesn't hit it. To deploy, run `./node_modules/.bin/grunt staging`, and then 
  `appcfg.py --oauth2 update build/`.
* **prod**: The real McCoy. Don't break it. To deploy, run `./node_modules/.bin/grunt prod`, and then 
  `appcfg.py --oauth2 update build/`.

We don't have much in the way of release procedures, so it just comes down to how paranoid you want to be. 
Some changes can go straight to prod. Some should go through dev first. Some through both dev and staging 
before prod. App Engine even allows you do to traffic splitting, so we could theoretically send N% of 
queries to staging if we're really paranoid about something. Use good judgement and run it by team memebers
if you're unsure.

If you're pushing to prod, please tag the commit you're pushing with the next available "v1,v2,v3,..." tag, 
and remember to git push --tags. That way if we need to roll back we have a sense of what used to be in
production.
