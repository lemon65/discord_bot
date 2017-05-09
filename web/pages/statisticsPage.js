const React = require('react')
const moment = require('moment')
require('moment-timezone')

const pageTitle = 'Discord statistics'

const initialState = {
  totalMessages: -1,
  messagesInLastWeek: -1,
  messagesInLastMonth: -1,
  dailyMessageCounts: [],
}

const formatDate = epochMs => moment(epochMs).tz('UTC').format('YYYY-MM-DD')

const dailyMessageCountTable = dailyMessageCounts =>
  <table>
    <thead>
      <tr>
          <td>Date</td>
          <td>Messages</td>
      </tr>
    </thead>
    <tbody>
      {dailyMessageCounts.map(x =>
        <tr key={x.epoch}>
          <td>{formatDate(x.epoch)}</td>
          <td>{x.count}</td>
        </tr>
      )}
    </tbody>
  </table>

const renderPage = state =>
  <div>
    <h1>Discord statistics</h1>
    <p>Total messages {state.totalMessages}</p>
    <p>Messages in last week {state.messagesInLastWeek}</p>
    <p>Messages in last month {state.messagesInLastMonth}</p>
    {dailyMessageCountTable(state.dailyMessageCounts)}
  </div>

module.exports = {
  pageTitle,
  initialState,
  renderPage,
}
