const Promise = require('bluebird')
const crypto = require('crypto')
const path = require('path')
const express = require('express')
const ReactDOMServer = require('react-dom/server')

const db = require('./db')

const basePage = require('./pages/basePage')
const statisticsPage = require('./pages/statisticsPage')

const checksumPromise = filePath => new Promise((resolve, reject) => {
  require('fs').readFile(filePath, (error, fileContent) => {
    if (error) {
      reject(error)
    } else {
      resolve(crypto.createHash('md5').update(fileContent).digest('hex'))
    }
  })
})

const serveStaticResource = filePath => (req, res, next) => {
  checksumPromise(filePath).then(checksum => {
    if (req.query.checksum == checksum) {
      const oneYearInSeconds = 60 * 60 * 24 * 356
      res.setHeader('Cache-Control', `public, max-age=${oneYearInSeconds}`)
      res.sendFile(filePath)
    } else {
      res.status(404).end()
    }
  })
  .catch(next)
}

const app = express()

const buildInitialState = (path, params) => {
  switch (path) {
  case '/':
    return Promise.join(
      db.findMessageCount(),
      db.messagesInLastNDays(7),
      db.messagesInLastNDays(30),
      db.findDailyMessageCounts(30),
      (totalMessages, messagesInLastWeek, messagesInLastMonth, dailyMessageCounts) => ({
        totalMessages,
        messagesInLastWeek,
        messagesInLastMonth,
        dailyMessageCounts,
      })
    )

  default:
    return Promise.resolve({})
  }
}

app.get('*', (req, res, next) => {
  console.log(`Requested ${req.originalUrl}`)
  const path = req.originalUrl
  if (path === '/') {
    const page = statisticsPage // TODO

    Promise.join(
      buildInitialState(path, req.query),
      checksumPromise(bundleJsFilePath),
      (state, bundleJsChecksum) => {
        const initialState = Object.assign(page.initialState, state)
        res.send(ReactDOMServer.renderToString(basePage(page, initialState, { bundleJsChecksum })))
      }
    ).catch(next)
  } else {
    next()
  }
})

const bundleJsFilePath = path.resolve(`${__dirname}/.generated/bundle.js`)
app.get('/bundle.js', serveStaticResource(bundleJsFilePath))

app.listen(3000, () => {
  console.log('Listening on port 3000')
})
