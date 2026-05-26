import subprocess
import json
import csv

def build_image():
    status = False
    print("Building the appliction!!")
    build_status= subprocess.run(['docker',"compose","up","-d"])
    if build_status.returncode == 0:
        status = True
        print("Build completed successfully with the latest tag!!")
        result = subprocess.run(
        ["docker", "images", "--format", "{{.Repository}},{{.Tag}},{{.ID}}"],
        capture_output=True,
        text=True
    )
        # Check if the command was successful
        if result.returncode == 0:
            status = True
            # Split the output into lines
            lines = result.stdout.strip().split('\n')
            
            # Write to a CSV file
            with open('local_docker_images.csv', 'w', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                # Write the header
                csv_writer.writerow(['Repository', 'Tag', 'Image ID'])
                # Write the image data
                for line in lines:
                    csv_writer.writerow(line.split(','))
        else:
            status = False
            print("Error:", result.stderr)
    else:
        status = False
        print(f"Build failed due to {build_status.returncode}")
    return status


def get_images_tags():
    file_name = "repo_images.csv"
    status = False
    command = "curl -X GET 'https://hub.comcast.net/svc/registry/schedule-tracker/index/' -H 'accept: application/json'"
    all_images = subprocess.run(command,shell=True,capture_output=True, text=True)
    if all_images.returncode == 0:
        status = True
        image_list = []
        result = json.loads(all_images.stdout.strip())
        images = result["images"]
        for image in images:
            image_dict = {}
            command = f"curl -X GET 'https://hub.comcast.net/svc/registry/{image}/tags' -H 'accept: application/json'"
            image_tags = subprocess.run(command,shell=True, capture_output=True, text=True)
            if image_tags.returncode == 0:
                output_string = json.loads(image_tags.stdout.strip())
                tags = output_string["tags"]
                latest_tag = tags[0]
                image_name = output_string["image"]
                image_dict["image"] = image_name
                image_dict["latest_tag"] = latest_tag
                image_list.append(image_dict)
                status = True
            else:
                status = False
                print("Error:", image_tags.stderr)
        with open(file_name,"w", newline='') as csv_file:
            csv_writer = csv.DictWriter(csv_file,fieldnames=image_list[0].keys())
            csv_writer.writeheader()
            csv_writer.writerows(image_list)
    else:
        status = False
        print("Error:", all_images.stderr)
    return status


build_status = build_image()
if build_status:
    subprocess.run("cat local_docker_images.csv", shell=True)
    print("Images are successfully built!! Checking the repo for the recent version of the images!!")
    image_tag_status = get_images_tags()
    if image_tag_status:
        print("Please check the recent tags of the images in repo_images.csv ")
        subprocess.run("cat repo_images.csv", shell=True)

