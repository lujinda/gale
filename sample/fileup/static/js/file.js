$(document).ready(function(){
    $('#file_input').change(function(){
        $('#up_wrap').ajaxSubmit({
            error: function(){
                alert('上传失败');
            },
            success: function(response){
                var error = response['error'];
                if (error){
                    alert(error);
                }else{
                    $('#img').attr('src', response['img_url']);
                }
            },
        });
    });
});
function choose_file(){
    $('#file_input').click();
}

