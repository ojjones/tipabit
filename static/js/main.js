
function getTipLogs(object)
{
    $.get("http://localhost:8080/get_logs",                                         
      function(data, status){
        if (data)
        {
            var length = data.logs.length;
            var text = ""
            for (i= 0; i < length; i++)
            {
              var text = $("<li class=list-group-item></li>").text(data.logs[i].date + " " +
                                             data.logs[i].tip_receiver + " " +
                                             data.logs[i].amount + "\n");
              $(object).append(text);
            }
        }
    }); 
}
